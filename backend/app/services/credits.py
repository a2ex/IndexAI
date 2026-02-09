import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.url import URL
from app.models.credit import CreditTransaction, TransactionType

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    pass


class CreditService:
    """
    Credit management: debit, refund, history.
    Rules:
    - 1 credit = 1 URL submitted
    - Debit at submission time
    - Auto-refund if not indexed after 14 days
    - No subscription, credits never expire
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        return user.credit_balance if user else 0

    async def debit_credits(self, user_id: uuid.UUID, url_ids: list[uuid.UUID]) -> bool:
        """Debit credits for submitted URLs."""
        count = len(url_ids)
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user or user.credit_balance < count:
            balance = user.credit_balance if user else 0
            raise InsufficientCreditsError(
                f"Balance: {balance}, required: {count}"
            )

        user.credit_balance -= count

        # Batch fetch all URLs
        url_result = await self.db.execute(select(URL).where(URL.id.in_(url_ids)))
        url_map = {u.id: u for u in url_result.scalars().all()}

        for url_id in url_ids:
            tx = CreditTransaction(
                user_id=user_id,
                amount=-1,
                type=TransactionType.debit,
                description="URL submission",
                url_id=url_id,
            )
            self.db.add(tx)

            url_obj = url_map.get(url_id)
            if url_obj:
                url_obj.credit_debited = True

        await self.db.flush()
        return True

    async def refund_credits(self, user_id: uuid.UUID, url_ids: list[uuid.UUID]) -> int:
        """Refund credits for non-indexed URLs after the delay."""
        # Batch fetch user and URLs
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalars().first()
        if not user:
            return 0

        url_result = await self.db.execute(select(URL).where(URL.id.in_(url_ids)))
        url_objects = url_result.scalars().all()

        refunded = 0
        for url_obj in url_objects:
            if url_obj.credit_debited and not url_obj.credit_refunded and not url_obj.is_indexed:
                user.credit_balance += 1
                url_obj.credit_refunded = True
                url_obj.status = "recredited"

                tx = CreditTransaction(
                    user_id=user_id,
                    amount=1,
                    type=TransactionType.refund,
                    description="Auto-refund: URL not indexed after 14 days",
                    url_id=url_obj.id,
                )
                self.db.add(tx)
                refunded += 1

        await self.db.flush()
        logger.info(f"Refunded {refunded} credits for user {user_id}")
        return refunded

    async def add_credits(self, user_id: uuid.UUID, amount: int, description: str = "Credit purchase") -> int:
        """Add credits to a user's balance."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise ValueError("User not found")

        user.credit_balance += amount

        tx = CreditTransaction(
            user_id=user_id,
            amount=amount,
            type=TransactionType.purchase,
            description=description,
        )
        self.db.add(tx)
        await self.db.flush()
        return user.credit_balance
