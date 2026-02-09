import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class URLStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    indexing = "indexing"
    verifying = "verifying"
    indexed = "indexed"
    not_indexed = "not_indexed"
    recredited = "recredited"


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[URLStatus] = mapped_column(
        SAEnum(URLStatus, native_enum=False), default=URLStatus.pending
    )

    # Attempts per method
    google_api_attempts: Mapped[int] = mapped_column(Integer, default=0)
    google_api_last_status: Mapped[str | None] = mapped_column(String)
    indexnow_attempts: Mapped[int] = mapped_column(Integer, default=0)
    indexnow_last_status: Mapped[str | None] = mapped_column(String)
    sitemap_ping_attempts: Mapped[int] = mapped_column(Integer, default=0)
    social_signal_attempts: Mapped[int] = mapped_column(Integer, default=0)
    backlink_ping_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Verification results
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    check_count: Mapped[int] = mapped_column(Integer, default=0)
    check_method: Mapped[str | None] = mapped_column(String)

    # Indexation proof
    indexed_title: Mapped[str | None] = mapped_column(Text)
    indexed_snippet: Mapped[str | None] = mapped_column(Text)

    # Credit
    credit_debited: Mapped[bool] = mapped_column(Boolean, default=False)
    credit_refunded: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pre-check: was this URL already indexed before we tried?
    pre_indexed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Was this URL ever confirmed as NOT indexed by a verification check?
    verified_not_indexed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    project: Mapped["Project"] = relationship(back_populates="urls")
    indexing_logs: Mapped[list["IndexingLog"]] = relationship(back_populates="url")
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(back_populates="url")
