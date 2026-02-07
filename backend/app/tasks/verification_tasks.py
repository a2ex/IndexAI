import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from celery_app import celery
from app.config import settings
from app.models.url import URL, URLStatus
from app.services.verification.checker import IndexationChecker
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


async def _check_urls(min_age_days: int = 0, max_age_days: int = 1):
    session_factory = _get_session_factory()
    async with session_factory() as db:
        now = datetime.utcnow()
        min_date = now - timedelta(days=max_age_days)
        max_date = now - timedelta(days=min_age_days)

        result = await db.execute(
            select(URL).where(
                and_(
                    URL.status.in_([URLStatus.submitted, URLStatus.indexing]),
                    URL.submitted_at >= min_date,
                    URL.submitted_at <= max_date,
                )
            )
        )
        urls = result.scalars().all()

        if not urls:
            logger.info(f"No URLs to check for age {min_age_days}-{max_age_days} days")
            return

        checker = IndexationChecker({
            "custom_search_api_key": settings.GOOGLE_CUSTOM_SEARCH_API_KEY,
            "cse_id": settings.GOOGLE_CSE_ID,
        })

        for url_obj in urls:
            try:
                check_result = await checker.check_url(url_obj.url)

                url_obj.last_checked_at = now
                url_obj.check_count += 1
                url_obj.check_method = check_result.get("method")

                if check_result.get("is_indexed"):
                    url_obj.is_indexed = True
                    url_obj.indexed_at = now
                    url_obj.status = URLStatus.indexed
                    url_obj.indexed_title = check_result.get("title")
                    url_obj.indexed_snippet = check_result.get("snippet")
                    logger.info(f"URL indexed: {url_obj.url}")
                    await notify_url_indexed(db, url_obj)

            except Exception as e:
                logger.error(f"Verification failed for {url_obj.url}: {e}")

        await db.commit()
        logger.info(f"Checked {len(urls)} URLs ({min_age_days}-{max_age_days} days old)")


@celery.task(name="app.tasks.verification_tasks.check_recent_urls")
def check_recent_urls():
    """Check URLs submitted less than 24h ago."""
    asyncio.get_event_loop().run_until_complete(_check_urls(0, 1))


@celery.task(name="app.tasks.verification_tasks.check_pending_urls")
def check_pending_urls(min_age_days: int = 1, max_age_days: int = 3):
    """Check pending URLs within a given age range."""
    asyncio.get_event_loop().run_until_complete(_check_urls(min_age_days, max_age_days))
