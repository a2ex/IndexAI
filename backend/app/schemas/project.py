import uuid
import ipaddress
from datetime import datetime
from urllib.parse import urlparse
from pydantic import BaseModel, field_validator
from app.schemas.url import URLResponse

MAX_URLS_PER_BATCH = 1000


def _validate_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty")

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL must use http or https: {url}")

    if not parsed.netloc:
        raise ValueError(f"Invalid URL (no host): {url}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"Invalid URL (no hostname): {url}")

    # Block private/reserved IPs
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_reserved or ip.is_loopback:
            raise ValueError(f"URLs pointing to private/reserved IPs are not allowed: {url}")
    except ValueError as e:
        if "private" in str(e) or "reserved" in str(e) or "loopback" in str(e):
            raise
        # Not an IP, it's a hostname — that's fine

    # Block localhost variants
    if hostname in ("localhost", "localhost.localdomain"):
        raise ValueError(f"URLs pointing to localhost are not allowed: {url}")

    return url


def _validate_url_list(urls: list[str]) -> list[str]:
    if not urls:
        raise ValueError("At least one URL is required")
    if len(urls) > MAX_URLS_PER_BATCH:
        raise ValueError(f"Maximum {MAX_URLS_PER_BATCH} URLs per batch")

    validated = [_validate_url(u) for u in urls]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for u in validated:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return unique


class IndexNowConfig(BaseModel):
    host: str
    api_key: str
    key_location: str


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    urls: list[str]
    indexnow_config: IndexNowConfig | None = None

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        return _validate_url_list(v)


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    total_urls: int
    indexed_count: int
    failed_count: int
    main_domain: str | None
    gsc_service_account_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    total_urls: int
    indexed_count: int
    not_indexed_count: int
    recredited_count: int
    pending_count: int
    main_domain: str | None
    created_at: datetime


class ProjectStatus(BaseModel):
    total: int
    indexed: int
    pending: int
    not_indexed: int
    recredited: int
    verifying: int = 0
    indexed_by_service: int = 0
    success_rate: float
    urls: list[URLResponse]
    urls_total: int = 0  # total matching filter (for pagination)
    limit: int = 100
    offset: int = 0


class ProjectDetail(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    total_urls: int
    indexed_count: int
    failed_count: int
    main_domain: str | None
    gsc_service_account_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    urls: list[URLResponse] = []

    model_config = {"from_attributes": True}


class AddUrls(BaseModel):
    urls: list[str]

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        return _validate_url_list(v)


class AddUrlsResponse(BaseModel):
    added: int
    total_urls: int
    credits_debited: int


class GscSitemapInfo(BaseModel):
    path: str
    lastSubmitted: str
    urls_count: int
    isPending: bool
    imported: bool = False
    imported_urls: int = 0
    imported_at: str | None = None


class GscImportRequest(BaseModel):
    sitemap_urls: list[str]


class GscImportResponse(BaseModel):
    added: int
    duplicates_skipped: int
    credits_debited: int


class IndexingSpeedStats(BaseModel):
    indexed_24h: int = 0
    indexed_48h: int = 0
    indexed_72h: int = 0
    indexed_7d: int = 0
    total_submitted: int = 0
    pct_24h: float = 0.0
    pct_48h: float = 0.0
    pct_72h: float = 0.0
    pct_7d: float = 0.0


class MethodStats(BaseModel):
    total_attempts: int = 0
    success: int = 0
    error: int = 0
    rate: float = 0.0


class IndexingStatsResponse(BaseModel):
    speed: IndexingSpeedStats
    methods: dict[str, MethodStats]
    indexed_by_service: int = 0
