import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class TransactionType(str, enum.Enum):
    purchase = "purchase"
    debit = "debit"
    refund = "refund"
    bonus = "bonus"


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, native_enum=False), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    url_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("urls.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user: Mapped["User"] = relationship(back_populates="credit_transactions")
    url: Mapped["URL | None"] = relationship(back_populates="credit_transactions")
