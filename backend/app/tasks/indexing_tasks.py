import asyncio
import logging
from datetime import datetime, timezone

def _utcnow() -> datetime:
    """Naive UTC datetime compatible with TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
from urllib.parse import urlparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from celery_app import celery
from app.config import settings
from app.models.url import URL, URLStatus
from app.models.indexing_log import IndexingLog
from app.models.project import Project
from app.models.user import User
from app.models.credit import CreditTransaction, TransactionType
from app.services.indexing.method_queue import (
    enqueue_url_methods,
    pop_eligible_jobs,
    check_rate_limit,
    acquire_url_lock,
    release_url_lock,
    requeue_job,
    get_queue_stats,
    MAX_RETRIES,
    BACKOFF_BASE,
)
from app.services.service_account_manager import ServiceAccountManager
from app.services.verification.checker import IndexationChecker, build_checker_for_project
from app.services.notifications import notify_url_indexed

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _get_session_factory():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


# ---------------------------------------------------------------------------
# Submit URLs: set status + enqueue jobs into Redis
# ---------------------------------------------------------------------------

async def _build_checker(db: AsyncSession, project_id: str) -> IndexationChecker:
    return await build_checker_for_project(db, project_id)


async def _mark_already_indexed(db: AsyncSession, url_obj: URL, user_id, check_result: dict):
    """Mark a URL as already indexed and refund the credit."""
    now = _utcnow()
    url_obj.is_indexed = True
    url_obj.indexed_at = now
    url_obj.status = URLStatus.indexed
    url_obj.last_checked_at = now
    url_obj.check_count += 1
    url_obj.check_method = check_result.get("method")
    url_obj.indexed_title = check_result.get("title")
    url_obj.indexed_snippet = check_result.get("snippet")

    # Refund credit
    if url_obj.credit_debited and not url_obj.credit_refunded:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalars().first()
        if user:
            user.credit_balance += 1
            url_obj.credit_refunded = True
            db.add(CreditTransaction(
                user_id=user_id,
                amount=1,
                type=TransactionType.refund,
                description="Pre-check: already indexed",
                url_id=url_obj.id,
            ))

    try:
        await notify_url_indexed(db, url_obj)
    except Exception as e:
        logger.warning(f"Notification failed for {url_obj.url}: {e}")
    await db.commit()


async def _submit_urls(project_id: str, url_ids: list[str], indexnow_config: dict | None):
    session_factory = _get_session_factory()

    async with session_factory() as db:
        checker = await _build_checker(db, project_id)
        # Get user_id for refunds
        proj_result = await db.execute(select(Project).where(Project.id == project_id))
        project = proj_result.scalars().first()
        if not project:
            logger.error(f"Project {project_id} not found")
            return
        user_id = project.user_id

        already_indexed = 0
        submitted = 0

        for url_id in url_ids:
            result = await db.execute(select(URL).where(URL.id == url_id))
            url_obj = result.scalars().first()
            if not url_obj:
                continue

            # Pre-check: is this URL already indexed?
            try:
                check_result = await checker.check_url(url_obj.url)
                if check_result.get("is_indexed"):
                    await _mark_already_indexed(db, url_obj, user_id, check_result)
                    already_indexed += 1
                    logger.info(f"Pre-check: already indexed, skipped: {url_obj.url}")
                    continue
            except Exception as e:
                await db.rollback()
                logger.warning(f"Pre-check failed for {url_obj.url}: {e}, submitting anyway")

            # Not indexed — submit for indexing
            url_obj.status = "submitted"
            url_obj.submitted_at = _utcnow()
            await db.commit()

            enqueue_url_methods(
                url_id=str(url_obj.id),
                project_id=project_id,
                indexnow_config=indexnow_config,
            )
            submitted += 1

    logger.info(
        f"Project {project_id}: {submitted} submitted, "
        f"{already_indexed} already indexed (refunded)"
    )


@celery.task(name="app.tasks.indexing_tasks.submit_urls_for_indexing")
def submit_urls_for_indexing(project_id: str, url_ids: list[str], indexnow_config: dict | None):
    """Celery task to submit URLs for indexing via method queue."""
    asyncio.run(_submit_urls(project_id, url_ids, indexnow_config))


async def _submit_single_url(url_id: str):
    session_factory = _get_session_factory()
    async with session_factory() as db:
        result = await db.execute(select(URL).where(URL.id == url_id))
        url_obj = result.scalars().first()
        if not url_obj:
            return

        url_obj.status = "submitted"
        url_obj.submitted_at = _utcnow()
        await db.commit()

        enqueue_url_methods(
            url_id=str(url_obj.id),
            project_id=str(url_obj.project_id),
        )


@celery.task(name="app.tasks.indexing_tasks.submit_single_url_task")
def submit_single_url_task(url_id: str):
    """Celery task to re-submit a single URL."""
    asyncio.run(_submit_single_url(url_id))


# ---------------------------------------------------------------------------
# Reset quotas (unchanged)
# ---------------------------------------------------------------------------

async def _reset_quotas():
    session_factory = _get_session_factory()
    async with session_factory() as db:
        sa_manager = ServiceAccountManager(db)
        await sa_manager.reset_all_quotas()


@celery.task(name="app.tasks.indexing_tasks.reset_service_account_quotas")
def reset_service_account_quotas():
    """Reset daily quotas for all service accounts."""
    asyncio.run(_reset_quotas())


# ---------------------------------------------------------------------------
# Process pending URLs: enqueue instead of fire-all-at-once
# ---------------------------------------------------------------------------

async def _process_pending_urls():
    """Pick up URLs in 'pending' status, pre-check indexation, then enqueue."""
    session_factory = _get_session_factory()

    async with session_factory() as db:
        result = await db.execute(
            select(URL)
            .where(URL.status == URLStatus.pending)
            .order_by(URL.created_at.asc())
            .limit(200)
        )
        pending_urls = result.scalars().all()
        if not pending_urls:
            logger.info("No pending URLs to process")
            return

        # Cache user_ids and checkers per project
        user_cache: dict[str, object] = {}
        checker_cache: dict[str, IndexationChecker] = {}

        submitted = 0
        already_indexed = 0
        for url_obj in pending_urls:
            # Get user_id for this URL's project
            pid = str(url_obj.project_id)
            if pid not in user_cache:
                proj_res = await db.execute(select(Project.user_id).where(Project.id == pid))
                row = proj_res.first()
                user_cache[pid] = row[0] if row else None
            user_id = user_cache[pid]

            # Build checker per project (cached)
            if pid not in checker_cache:
                checker_cache[pid] = await _build_checker(db, pid)
            checker = checker_cache[pid]

            # Pre-check
            try:
                check_result = await checker.check_url(url_obj.url)
                if check_result.get("is_indexed") and user_id:
                    await _mark_already_indexed(db, url_obj, user_id, check_result)
                    already_indexed += 1
                    continue
            except Exception as e:
                await db.rollback()
                logger.warning(f"Pre-check failed for {url_obj.url}: {e}, submitting anyway")

            url_obj.status = "submitted"
            url_obj.submitted_at = _utcnow()
            await db.commit()

            enqueue_url_methods(
                url_id=str(url_obj.id),
                project_id=pid,
            )
            submitted += 1

        logger.info(
            f"Pending URLs: {submitted} submitted, {already_indexed} already indexed"
        )


@celery.task(name="app.tasks.indexing_tasks.process_pending_urls")
def process_pending_urls():
    """Periodic task: enqueue pending URLs into the method queue."""
    asyncio.run(_process_pending_urls())


# ---------------------------------------------------------------------------
# Process method queue: the central processor (Celery beat every 2 min)
# ---------------------------------------------------------------------------

async def _execute_method(db: AsyncSession, url_obj: URL, method: str, job: dict) -> dict:
    """Execute a single indexing method and return the result dict."""
    url = url_obj.url

    if method == "google_api":
        from app.services.indexing.google_indexing_api import submit_url_google_api
        sa_manager = ServiceAccountManager(db)
        sa = await sa_manager.get_next_available()
        if not sa:
            return {"success": False, "error": "no_sa_available"}
        result = submit_url_google_api(url, sa.json_key_path)
        await sa_manager.increment_usage(sa.id, 1)
        return {"success": True, "data": result}

    elif method == "indexnow":
        from app.services.indexing.indexnow import submit_indexnow
        indexnow_config = job.get("indexnow_config")
        if not indexnow_config and settings.INDEXNOW_API_KEY:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            indexnow_config = {
                "host": host,
                "api_key": settings.INDEXNOW_API_KEY,
                "key_location": f"https://{host}/{settings.INDEXNOW_API_KEY}.txt",
            }
        if not indexnow_config:
            return {"success": False, "error": "no_indexnow_config"}
        result = await submit_indexnow(
            [url],
            indexnow_config["host"],
            indexnow_config["api_key"],
            indexnow_config["key_location"],
        )
        return {"success": True, "data": result}

    elif method == "pingomatic":
        from app.services.indexing.social_signals import ping_web_services
        result = await ping_web_services(url)
        return {"success": True, "data": result}

    elif method == "websub":
        from app.services.indexing.social_signals import ping_web_services
        result = await ping_web_services(url)
        return {"success": True, "data": result}

    elif method == "archive_org":
        from app.services.indexing.social_signals import ping_web_services
        result = await ping_web_services(url)
        return {"success": True, "data": result}

    elif method == "backlink_pings":
        from app.services.indexing.backlink_pings import ping_backlink_trackers
        result = await ping_backlink_trackers(url)
        return {"success": True, "data": result}

    return {"success": False, "error": f"unknown_method: {method}"}


def _increment_attempt_counter(url_obj: URL, method: str, success: bool):
    """Update the per-method attempt counter and last_status on the URL model."""
    status_str = "success" if success else "error"

    if method == "google_api":
        url_obj.google_api_attempts += 1
        url_obj.google_api_last_status = status_str
    elif method == "indexnow":
        url_obj.indexnow_attempts += 1
        url_obj.indexnow_last_status = status_str
    elif method in ("pingomatic", "websub", "archive_org"):
        url_obj.social_signal_attempts += 1
    elif method == "backlink_pings":
        url_obj.backlink_ping_attempts += 1


async def _process_method_queue():
    """Pop eligible jobs from the Redis queue and execute them."""
    stats = get_queue_stats()
    logger.info(f"Method queue stats: {stats}")

    jobs = pop_eligible_jobs(batch_size=50)
    if not jobs:
        logger.info("No eligible jobs in method queue")
        return

    session_factory = _get_session_factory()
    processed = 0
    skipped = 0

    for job in jobs:
        url_id = job["url_id"]
        method = job["method"]
        attempt = job.get("attempt", 0)

        # Check rate limit
        if not check_rate_limit(method):
            logger.info(f"Rate limit exceeded for {method}, requeuing")
            requeue_job(job, delay=30)
            skipped += 1
            continue

        # Acquire URL lock
        if not acquire_url_lock(url_id):
            logger.info(f"URL {url_id} is locked, requeuing {method}")
            requeue_job(job, delay=15)
            skipped += 1
            continue

        try:
            async with session_factory() as db:
                result = await db.execute(select(URL).where(URL.id == url_id))
                url_obj = result.scalars().first()

                if not url_obj:
                    logger.warning(f"URL {url_id} not found, dropping job")
                    continue

                # Skip if already indexed
                if url_obj.is_indexed:
                    logger.info(f"URL {url_id} already indexed, skipping {method}")
                    continue

                try:
                    method_result = await _execute_method(db, url_obj, method, job)
                    success = method_result.get("success", False)

                    # Log result
                    log = IndexingLog(
                        url_id=url_obj.id,
                        method=method,
                        status="success" if success else "error",
                        response_body=str(method_result),
                    )
                    db.add(log)

                    _increment_attempt_counter(url_obj, method, success)

                    if not success:
                        if attempt < MAX_RETRIES - 1:
                            retry_job = {**job, "attempt": attempt + 1}
                            delay = min(BACKOFF_BASE * (2 ** attempt), 3600)
                            requeue_job(retry_job, delay=delay)
                            logger.warning(
                                f"{method} failed for {url_id} (attempt {attempt + 1}), "
                                f"retrying in {delay}s"
                            )
                        else:
                            logger.error(
                                f"{method} failed for {url_id} after {MAX_RETRIES} attempts, "
                                f"giving up"
                            )

                    # Update URL status to indexing if still submitted
                    if url_obj.status == URLStatus.submitted:
                        url_obj.status = "indexing"

                    # Transition to verifying after the last method (google_api)
                    if method == "google_api" and success and url_obj.status == URLStatus.indexing:
                        url_obj.status = URLStatus.verifying

                    await db.commit()
                    processed += 1

                except Exception as e:
                    logger.error(f"Error executing {method} for {url_id}: {e}")
                    try:
                        await db.rollback()
                        log = IndexingLog(
                            url_id=url_obj.id,
                            method=method,
                            status="error",
                            response_body=str(e)[:500],
                        )
                        db.add(log)
                        _increment_attempt_counter(url_obj, method, False)
                        await db.commit()
                    except Exception as inner_e:
                        logger.error(f"Failed to log error for {url_id}: {inner_e}")
                        await db.rollback()

                    # Retry on exception
                    if attempt < MAX_RETRIES - 1:
                        retry_job = {**job, "attempt": attempt + 1}
                        delay = min(BACKOFF_BASE * (2 ** attempt), 3600)
                        requeue_job(retry_job, delay=delay)

        finally:
            release_url_lock(url_id)

    logger.info(f"Method queue: processed={processed}, skipped={skipped}")


@celery.task(name="app.tasks.indexing_tasks.process_method_queue")
def process_method_queue():
    """Periodic task: process the method queue (runs every 2 minutes)."""
    asyncio.run(_process_method_queue())
