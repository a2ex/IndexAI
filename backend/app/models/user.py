import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    credit_balance: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    projects: Mapped[list["Project"]] = relationship(back_populates="user")
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(back_populates="user")
    notification_settings: Mapped[Optional["NotificationSettings"]] = relationship(back_populates="user", uselist=False)
