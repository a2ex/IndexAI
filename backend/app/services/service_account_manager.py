import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.service_account import ServiceAccount

logger = logging.getLogger(__name__)


class ServiceAccountManager:
    """Manages a pool of Google service accounts with quota rotation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_next_available(self) -> ServiceAccount | None:
        """Get the next service account with available quota (round-robin)."""
        result = await self.db.execute(
            select(ServiceAccount)
            .where(ServiceAccount.is_active == True)
            .where(ServiceAccount.used_today < ServiceAccount.daily_quota)
            .order_by(ServiceAccount.used_today.asc())
        )
        return result.scalars().first()

    async def get_total_remaining_quota(self) -> int:
        """Get total remaining quota across all active service accounts."""
        result = await self.db.execute(
            select(ServiceAccount).where(ServiceAccount.is_active == True)
        )
        accounts = result.scalars().all()
        return sum(max(0, sa.daily_quota - sa.used_today) for sa in accounts)

    async def increment_usage(self, sa_id: uuid.UUID, count: int = 1):
        """Increment the usage counter for a service account."""
        result = await self.db.execute(
            select(ServiceAccount).where(ServiceAccount.id == sa_id)
        )
        sa = result.scalars().first()
        if sa:
            sa.used_today += count
            await self.db.flush()

    async def disable_account(self, sa_id: uuid.UUID):
        """Temporarily disable a service account (e.g., after 429/403 errors)."""
        result = await self.db.execute(
            select(ServiceAccount).where(ServiceAccount.id == sa_id)
        )
        sa = result.scalars().first()
        if sa:
            sa.is_active = False
            await self.db.flush()
            logger.warning(f"Service account {sa.email} disabled")

    async def reset_all_quotas(self):
        """Reset daily quotas for all service accounts (run at midnight UTC)."""
        result = await self.db.execute(select(ServiceAccount))
        for sa in result.scalars().all():
            sa.used_today = 0
            sa.last_reset_at = datetime.utcnow()
            sa.is_active = True
        await self.db.commit()
        logger.info("All service account quotas reset")
