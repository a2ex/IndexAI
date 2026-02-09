import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from celery_app import celery
from app.config import settings
from app.models.notification import NotificationSettings
from app.models.project import Project
from app.models.url import URL, URLStatus
from app.models.user import User
from app.services.notifications import send_email_digest

logger = logging.getLogger(__name__)

def _get_session_factory():
    # Always create a fresh engine — each asyncio.run() creates a new event loop,
    # so cached asyncpg connections become attached to a stale loop
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _send_daily_digest():
    session_factory = _get_session_factory()
    async with session_factory() as db:
        # Find all users with email digest enabled
        result = await db.execute(
            select(NotificationSettings).where(NotificationSettings.email_digest_enabled == True)
        )
        all_settings = result.scalars().all()

        if not all_settings:
            logger.info("No users with email digest enabled")
            return

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).replace(tzinfo=None)

        for notif in all_settings:
            try:
                # Get user
                user_result = await db.execute(
                    select(User).where(User.id == notif.user_id)
                )
                user = user_result.scalars().first()
                if not user:
                    continue

                # Get user's projects
                projects_result = await db.execute(
                    select(Project).where(Project.user_id == user.id)
                )
                projects = projects_result.scalars().all()
                if not projects:
                    continue

                project_ids = [p.id for p in projects]
                project_names = {p.id: p.name for p in projects}

                # Get URLs indexed in the last 24h
                urls_result = await db.execute(
                    select(URL).where(
                        and_(
                            URL.project_id.in_(project_ids),
                            URL.status == URLStatus.indexed,
                            URL.indexed_at >= cutoff,
                        )
                    )
                )
                urls = urls_result.scalars().all()

                if not urls:
                    continue

                urls_data = [
                    {
                        "url": u.url,
                        "project": project_names.get(u.project_id, "—"),
                        "indexed_at": u.indexed_at.strftime("%Y-%m-%d %H:%M") if u.indexed_at else "—",
                    }
                    for u in urls
                ]

                to_email = notif.email_digest_address or user.email
                send_email_digest(to_email, urls_data)
                logger.info(f"Daily digest sent to {to_email} — {len(urls_data)} URLs")

            except Exception as e:
                logger.error(f"Daily digest failed for user {notif.user_id}: {e}")


@celery.task(name="app.tasks.notification_tasks.send_daily_digest")
def send_daily_digest():
    """Send daily email digest of indexed URLs to subscribed users."""
    asyncio.run(_send_daily_digest())
