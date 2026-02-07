import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from celery_app import celery
from app.config import settings
from app.models.url import URL
from app.models.indexing_log import IndexingLog
from app.services.indexing.orchestrator import IndexingOrchestrator
from app.services.service_account_manager import ServiceAccountManager

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _get_session_factory():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def _submit_urls(project_id: str, url_ids: list[str], indexnow_config: dict | None):
    session_factory = _get_session_factory()
    async with session_factory() as db:
        sa_manager = ServiceAccountManager(db)
        orchestrator = IndexingOrchestrator(sa_manager)

        sitemap_url = f"{settings.BASE_URL}/sitemaps/{project_id}.xml"

        # Wave throttling: check available SA quota
        remaining_quota = await sa_manager.get_total_remaining_quota()
        if remaining_quota == 0:
            logger.warning(f"No SA quota available, {len(url_ids)} URLs will be processed by periodic task")
            return

        # Process up to quota limit; rest will be picked up by process_pending_urls
        processable_ids = url_ids[:remaining_quota]
        skipped = len(url_ids) - len(processable_ids)
        if skipped > 0:
            logger.info(f"Wave throttle: processing {len(processable_ids)}/{len(url_ids)} URLs, {skipped} deferred")

        for url_id in processable_ids:
            result = await db.execute(select(URL).where(URL.id == url_id))
            url_obj = result.scalars().first()
            if not url_obj:
                continue

            url_obj.status = "submitted"
            url_obj.submitted_at = datetime.utcnow()
            await db.commit()

            try:
                results = await orchestrator.submit_url(
                    url_obj.url,
                    indexnow_config=indexnow_config,
                    sitemap_url=sitemap_url,
                )

                # Log each method result
                for method, method_result in results.items():
                    log = IndexingLog(
                        url_id=url_obj.id,
                        method=method,
                        status="success" if method_result.get("success") else "error",
                        response_body=str(method_result),
                    )
                    db.add(log)

                    # Update attempt counters
                    if method == "google_api":
                        url_obj.google_api_attempts += 1
                        url_obj.google_api_last_status = "success" if method_result.get("success") else "error"
                    elif method == "indexnow":
                        url_obj.indexnow_attempts += 1
                        url_obj.indexnow_last_status = "success" if method_result.get("success") else "error"
                    elif method.startswith("sitemap_ping"):
                        url_obj.sitemap_ping_attempts += 1
                    elif method == "social_signals":
                        url_obj.social_signal_attempts += 1
                    elif method == "backlink_pings":
                        url_obj.backlink_ping_attempts += 1

            except Exception as e:
                logger.error(f"Failed to submit URL {url_obj.url}: {e}")
                log = IndexingLog(
                    url_id=url_obj.id,
                    method="orchestrator",
                    status="error",
                    response_body=str(e),
                )
                db.add(log)

            url_obj.status = "indexing"
            await db.commit()


@celery.task(name="app.tasks.indexing_tasks.submit_urls_for_indexing")
def submit_urls_for_indexing(project_id: str, url_ids: list[str], indexnow_config: dict | None):
    """Celery task to submit URLs for indexing via all methods."""
    asyncio.get_event_loop().run_until_complete(
        _submit_urls(project_id, url_ids, indexnow_config)
    )


async def _submit_single_url(url_id: str):
    session_factory = _get_session_factory()
    async with session_factory() as db:
        result = await db.execute(select(URL).where(URL.id == url_id))
        url_obj = result.scalars().first()
        if not url_obj:
            return

        sa_manager = ServiceAccountManager(db)
        orchestrator = IndexingOrchestrator(sa_manager)

        sitemap_url = f"{settings.BASE_URL}/sitemaps/{url_obj.project_id}.xml"

        url_obj.status = "submitted"
        url_obj.submitted_at = datetime.utcnow()
        await db.commit()

        results = await orchestrator.submit_url(url_obj.url, sitemap_url=sitemap_url)

        for method, method_result in results.items():
            log = IndexingLog(
                url_id=url_obj.id,
                method=method,
                status="success" if method_result.get("success") else "error",
                response_body=str(method_result),
            )
            db.add(log)

            if method == "google_api":
                url_obj.google_api_attempts += 1
                url_obj.google_api_last_status = "success" if method_result.get("success") else "error"
            elif method == "indexnow":
                url_obj.indexnow_attempts += 1
                url_obj.indexnow_last_status = "success" if method_result.get("success") else "error"
            elif method.startswith("sitemap_ping"):
                url_obj.sitemap_ping_attempts += 1
            elif method == "social_signals":
                url_obj.social_signal_attempts += 1
            elif method == "backlink_pings":
                url_obj.backlink_ping_attempts += 1

        url_obj.status = "indexing"
        await db.commit()


@celery.task(name="app.tasks.indexing_tasks.submit_single_url_task")
def submit_single_url_task(url_id: str):
    """Celery task to re-submit a single URL."""
    asyncio.get_event_loop().run_until_complete(_submit_single_url(url_id))


async def _reset_quotas():
    session_factory = _get_session_factory()
    async with session_factory() as db:
        sa_manager = ServiceAccountManager(db)
        await sa_manager.reset_all_quotas()


@celery.task(name="app.tasks.indexing_tasks.reset_service_account_quotas")
def reset_service_account_quotas():
    """Reset daily quotas for all service accounts."""
    asyncio.get_event_loop().run_until_complete(_reset_quotas())


async def _process_pending_urls():
    """Pick up URLs in 'pending' status and submit them if SA quota is available."""
    session_factory = _get_session_factory()
    async with session_factory() as db:
        sa_manager = ServiceAccountManager(db)
        remaining_quota = await sa_manager.get_total_remaining_quota()
        if remaining_quota == 0:
            logger.info("No SA quota available for pending URLs")
            return

        from app.models.url import URLStatus
        result = await db.execute(
            select(URL)
            .where(URL.status == URLStatus.pending)
            .order_by(URL.created_at.asc())
            .limit(remaining_quota)
        )
        pending_urls = result.scalars().all()
        if not pending_urls:
            logger.info("No pending URLs to process")
            return

        orchestrator = IndexingOrchestrator(sa_manager)
        processed = 0

        for url_obj in pending_urls:
            # Recheck quota each iteration (decrements as we go)
            sa = await sa_manager.get_next_available()
            if not sa:
                logger.info(f"SA quota exhausted after {processed} URLs")
                break

            url_obj.status = "submitted"
            url_obj.submitted_at = datetime.utcnow()
            await db.commit()

            try:
                sitemap_url = f"{settings.BASE_URL}/sitemaps/{url_obj.project_id}.xml"
                results = await orchestrator.submit_url(url_obj.url, sitemap_url=sitemap_url)

                for method, method_result in results.items():
                    log = IndexingLog(
                        url_id=url_obj.id,
                        method=method,
                        status="success" if method_result.get("success") else "error",
                        response_body=str(method_result),
                    )
                    db.add(log)

                    if method == "google_api":
                        url_obj.google_api_attempts += 1
                        url_obj.google_api_last_status = "success" if method_result.get("success") else "error"
                    elif method == "indexnow":
                        url_obj.indexnow_attempts += 1
                        url_obj.indexnow_last_status = "success" if method_result.get("success") else "error"
                    elif method.startswith("sitemap_ping"):
                        url_obj.sitemap_ping_attempts += 1
                    elif method == "social_signals":
                        url_obj.social_signal_attempts += 1
                    elif method == "backlink_pings":
                        url_obj.backlink_ping_attempts += 1

            except Exception as e:
                logger.error(f"Failed to submit pending URL {url_obj.url}: {e}")
                log = IndexingLog(
                    url_id=url_obj.id,
                    method="orchestrator",
                    status="error",
                    response_body=str(e),
                )
                db.add(log)

            url_obj.status = "indexing"
            processed += 1
            await db.commit()

        logger.info(f"Processed {processed} pending URLs")


@celery.task(name="app.tasks.indexing_tasks.process_pending_urls")
def process_pending_urls():
    """Periodic task: process pending URLs when SA quota is available."""
    asyncio.get_event_loop().run_until_complete(_process_pending_urls())
