import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class URLStatusEnum(str, Enum):
    pending = "pending"
    submitted = "submitted"
    indexing = "indexing"
    indexed = "indexed"
    not_indexed = "not_indexed"
    recredited = "recredited"


class URLResponse(BaseModel):
    id: uuid.UUID
    url: str
    status: str
    google_api_attempts: int
    indexnow_attempts: int
    sitemap_ping_attempts: int
    social_signal_attempts: int
    backlink_ping_attempts: int
    is_indexed: bool
    indexed_at: datetime | None
    last_checked_at: datetime | None
    check_count: int
    check_method: str | None
    indexed_title: str | None
    indexed_snippet: str | None
    credit_debited: bool
    credit_refunded: bool
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
