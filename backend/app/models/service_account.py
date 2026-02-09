import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ServiceAccount(Base):
    __tablename__ = "service_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    json_key_path: Mapped[str] = mapped_column(String, nullable=False)
    daily_quota: Mapped[int] = mapped_column(Integer, default=200)
    used_today: Mapped[int] = mapped_column(Integer, default=0)
    last_reset_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
