import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from celery_app import celery
from app.config import settings
from app.models.url import URL, URLStatus
from app.services.verification.checker import IndexationChecker, build_checker_for_project
from app.services.notifications import notify_url_indexed

logger = logging.getLogger(__name__)

def _get_session_factory():
    # Always create a fresh engine — solo pool uses a new event loop per asyncio.run()
    # so cached asyncpg connections become attached to a stale loop
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _process_url(db: AsyncSession, url_obj: URL, checker: IndexationChecker, label: str = ""):
    """Check a single URL's indexation with the given checker. Commits on success, rolls back on error."""
    try:
        if url_obj.status == URLStatus.submitted:
            url_obj.status = URLStatus.indexing
        elif url_obj.status == URLStatus.indexing:
            url_obj.status = URLStatus.verifying

        check_result = await checker.check_url(url_obj.url)

        checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        url_obj.last_checked_at = checked_at
        url_obj.check_count += 1
        url_obj.check_method = check_result.get("method")

        if check_result.get("is_indexed"):
            url_obj.is_indexed = True
            url_obj.indexed_at = checked_at
            url_obj.status = URLStatus.indexed
            url_obj.indexed_title = check_result.get("title")
            url_obj.indexed_snippet = check_result.get("snippet")
            logger.info(f"URL indexed{label}: {url_obj.url}")
            await notify_url_indexed(db, url_obj)
        elif check_result.get("is_indexed") is None:
            logger.warning(
                f"No reliable check method for {url_obj.url} "
                f"(method={check_result.get('method')})"
            )
        else:
            url_obj.status = URLStatus.not_indexed
            url_obj.verified_not_indexed = True
            logger.info(f"URL not indexed yet{label}: {url_obj.url}")

        await db.commit()

    except Exception as e:
        logger.error(f"Verification failed for {url_obj.url}: {e}")
        await db.rollback()


async def _verify_project_urls(project_id: str, url_ids: list[str]):
    """Check indexation for a list of URLs belonging to a single project."""
    session_factory = _get_session_factory()
    async with session_factory() as db:
        result = await db.execute(
            select(URL).where(URL.id.in_(url_ids), URL.project_id == project_id)
        )
        urls = result.scalars().all()
        if not urls:
            logger.info(f"No URLs found for project {project_id}")
            return

        checker = await build_checker_for_project(db, project_id)
        for url_obj in urls:
            await _process_url(db, url_obj, checker)

        logger.info(f"Verified {len(urls)} URLs for project {project_id}")


@celery.task(name="app.tasks.verification_tasks.verify_project_urls")
def verify_project_urls(project_id: str, url_ids: list[str]):
    """Verify URLs for a single project (dispatched per-project)."""
    asyncio.run(_verify_project_urls(project_id, url_ids))


async def _check_urls(min_age_days: int = 0, max_age_days: int = 1):
    session_factory = _get_session_factory()
    async with session_factory() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        min_date = now - timedelta(days=max_age_days)
        max_date = now - timedelta(days=min_age_days)

        result = await db.execute(
            select(URL).where(
                and_(
                    URL.status.in_([URLStatus.submitted, URLStatus.indexing, URLStatus.verifying, URLStatus.not_indexed]),
                    URL.submitted_at >= min_date,
                    URL.submitted_at <= max_date,
                )
            )
        )
        urls = result.scalars().all()

        if not urls:
            logger.info(f"No URLs to check for age {min_age_days}-{max_age_days} days")
            return

        # Group URLs by project_id and dispatch a task per project
        by_project: dict[str, list[str]] = defaultdict(list)
        for url_obj in urls:
            by_project[str(url_obj.project_id)].append(str(url_obj.id))

        for project_id, url_ids in by_project.items():
            verify_project_urls.delay(project_id, url_ids)

        logger.info(f"Dispatched verification for {len(urls)} URLs across {len(by_project)} projects ({min_age_days}-{max_age_days} days old)")


async def _check_single_url(url_id: str):
    """Check a single URL's indexation status."""
    session_factory = _get_session_factory()
    async with session_factory() as db:
        result = await db.execute(select(URL).where(URL.id == url_id))
        url_obj = result.scalars().first()
        if not url_obj:
            logger.error(f"URL not found: {url_id}")
            return

        checker = await build_checker_for_project(db, str(url_obj.project_id))
        await _process_url(db, url_obj, checker)


@celery.task(name="app.tasks.verification_tasks.check_single_url")
def check_single_url(url_id: str):
    """Force check indexation status for a single URL."""
    asyncio.run(_check_single_url(url_id))


async def _check_fresh_urls():
    """Check URLs submitted in the last 6 hours, skip recently checked."""
    session_factory = _get_session_factory()
    async with session_factory() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        min_date = now - timedelta(hours=6)
        recently_checked = now - timedelta(minutes=50)

        result = await db.execute(
            select(URL).where(
                and_(
                    URL.status.in_([URLStatus.submitted, URLStatus.indexing, URLStatus.verifying, URLStatus.not_indexed]),
                    URL.submitted_at >= min_date,
                    (URL.last_checked_at == None) | (URL.last_checked_at < recently_checked),
                )
            ).limit(100)
        )
        urls = result.scalars().all()

        if not urls:
            logger.info("No fresh URLs to check (<6h)")
            return

        # Group URLs by project_id and dispatch a task per project
        by_project: dict[str, list[str]] = defaultdict(list)
        for url_obj in urls:
            by_project[str(url_obj.project_id)].append(str(url_obj.id))

        for project_id, url_ids in by_project.items():
            verify_project_urls.delay(project_id, url_ids)

        logger.info(f"Fresh check: dispatched {len(urls)} URLs across {len(by_project)} projects (<6h old)")


@celery.task(name="app.tasks.verification_tasks.check_fresh_urls")
def check_fresh_urls():
    """Hourly check for URLs submitted in the last 6 hours."""
    asyncio.run(_check_fresh_urls())


@celery.task(name="app.tasks.verification_tasks.check_recent_urls")
def check_recent_urls():
    """Check URLs submitted less than 24h ago."""
    asyncio.run(_check_urls(0, 1))


@celery.task(name="app.tasks.verification_tasks.check_pending_urls")
def check_pending_urls(min_age_days: int = 1, max_age_days: int = 3):
    """Check pending URLs within a given age range."""
    asyncio.run(_check_urls(min_age_days, max_age_days))
