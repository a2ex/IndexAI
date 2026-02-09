import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    webhook_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    email_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    email_digest_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user: Mapped["User"] = relationship(back_populates="notification_settings")
