import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Enum as SAEnum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class ProjectStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    paused = "paused"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, native_enum=False), default=ProjectStatus.active
    )
    total_urls: Mapped[int] = mapped_column(Integer, default=0)
    indexed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    main_domain: Mapped[str | None] = mapped_column(String, nullable=True)
    gsc_service_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("service_accounts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user: Mapped["User"] = relationship(back_populates="projects")
    urls: Mapped[list["URL"]] = relationship(back_populates="project")
    imported_sitemaps: Mapped[list["ImportedSitemap"]] = relationship(back_populates="project")
    gsc_service_account: Mapped["ServiceAccount | None"] = relationship()
