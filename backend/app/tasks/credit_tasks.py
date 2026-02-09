import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from celery_app import celery
from app.config import settings
from app.models.url import URL, URLStatus
from app.models.project import Project
from app.services.credits import CreditService

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _get_session_factory():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def _auto_recredit():
    session_factory = _get_session_factory()
    async with session_factory() as db:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).replace(tzinfo=None)

        result = await db.execute(
            select(URL).where(
                and_(
                    URL.credit_debited == True,
                    URL.credit_refunded == False,
                    URL.is_indexed == False,
                    URL.submitted_at <= cutoff,
                    URL.status.in_([
                        URLStatus.submitted,
                        URLStatus.indexing,
                        URLStatus.not_indexed,
                    ]),
                )
            )
        )
        urls = result.scalars().all()

        if not urls:
            logger.info("No URLs eligible for auto-refund")
            return

        # Group by project to get user_id
        project_ids = set(u.project_id for u in urls)
        projects = {}
        for pid in project_ids:
            proj_result = await db.execute(select(Project).where(Project.id == pid))
            proj = proj_result.scalars().first()
            if proj:
                projects[pid] = proj

        credit_service = CreditService(db)
        total_refunded = 0

        for url_obj in urls:
            project = projects.get(url_obj.project_id)
            if not project:
                continue

            refunded = await credit_service.refund_credits(
                project.user_id, [url_obj.id]
            )
            total_refunded += refunded

        await db.commit()
        logger.info(f"Auto-refunded {total_refunded} credits for {len(urls)} URLs")


@celery.task(name="app.tasks.credit_tasks.auto_recredit_expired")
def auto_recredit_expired():
    """Auto-refund credits for URLs not indexed after 14 days."""
    asyncio.run(_auto_recredit())
