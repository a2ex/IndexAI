import csv
import io
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from app.database import get_db
from app.api.auth import get_current_user
from app.rate_limit import limiter
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.service_account import ServiceAccount
from app.models.url import URL, URLStatus


def _extract_main_domain(urls: list[str]) -> str | None:
    """Extract the most common domain from a list of URLs."""
    domains = []
    for u in urls:
        try:
            host = urlparse(u).hostname
            if host:
                domains.append(host.removeprefix("www."))
        except Exception:
            continue
    if not domains:
        return None
    return Counter(domains).most_common(1)[0][0]
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectSummary,
    ProjectDetail,
    ProjectStatus as ProjectStatusSchema,
    AddUrls,
    AddUrlsResponse,
    GscSitemapInfo,
    GscImportRequest,
    GscImportResponse,
    IndexingStatsResponse,
    IndexingSpeedStats,
    MethodStats,
)
from app.services.credits import CreditService, InsufficientCreditsError
from app.services.gsc_sitemaps import list_sitemaps, fetch_sitemap_urls, discover_sitemap_index
from app.config import settings
from app.models.imported_sitemap import ImportedSitemap

from app.models.url import URL as URLModel, URLStatus
from app.models.indexing_log import IndexingLog

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
@limiter.limit("10/minute")
async def create_project(
    request: Request,
    data: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a project and submit URLs for indexation."""
    credit_service = CreditService(db)

    # Check credits
    balance = await credit_service.get_balance(user.id)
    if balance < len(data.urls):
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Balance: {balance}, required: {len(data.urls)}",
        )

    # Create project
    project = Project(
        user_id=user.id,
        name=data.name,
        description=data.description,
        total_urls=len(data.urls),
        main_domain=_extract_main_domain(data.urls),
    )
    db.add(project)
    await db.flush()

    # Create URL entries
    url_objects = []
    for url_str in data.urls:
        url_obj = URL(project_id=project.id, url=url_str)
        db.add(url_obj)
        url_objects.append(url_obj)
    await db.flush()

    # Debit credits
    try:
        await credit_service.debit_credits(user.id, [u.id for u in url_objects])
    except InsufficientCreditsError:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    # Queue indexing tasks (Celery)
    from app.tasks.indexing_tasks import submit_urls_for_indexing

    indexnow_config = data.indexnow_config.model_dump() if data.indexnow_config else None
    submit_urls_for_indexing.delay(
        str(project.id),
        [str(u.id) for u in url_objects],
        indexnow_config,
    )

    await db.commit()
    return project


@router.get("", response_model=list[ProjectSummary])
@limiter.limit("60/minute")
async def list_projects(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects for the current user with computed URL counts."""
    # Load projects (lightweight, no URL eager loading)
    proj_result = await db.execute(
        select(Project)
        .where(Project.user_id == user.id)
        .order_by(Project.created_at.desc())
    )
    projects = proj_result.scalars().all()
    if not projects:
        return []

    # SQL aggregation: count URLs per project and status
    project_ids = [p.id for p in projects]
    count_result = await db.execute(
        select(
            URLModel.project_id,
            URLModel.status,
            func.count().label("cnt"),
        )
        .where(URLModel.project_id.in_(project_ids))
        .group_by(URLModel.project_id, URLModel.status)
    )
    # Build {project_id: {status: count}} map
    counts: dict[uuid.UUID, dict[str, int]] = {}
    for row in count_result.all():
        pid = row[0]
        status_val = row[1].value if hasattr(row[1], "value") else str(row[1])
        counts.setdefault(pid, {})[status_val] = row[2]

    summaries = []
    for p in projects:
        sc = counts.get(p.id, {})
        indexed = sc.get("indexed", 0)
        not_indexed = sc.get("not_indexed", 0)
        recredited = sc.get("recredited", 0)
        pending = sc.get("pending", 0) + sc.get("submitted", 0) + sc.get("indexing", 0) + sc.get("verifying", 0)
        summaries.append(ProjectSummary(
            id=p.id,
            name=p.name,
            status=p.status.value if hasattr(p.status, "value") else str(p.status),
            total_urls=p.total_urls,
            indexed_count=indexed,
            not_indexed_count=not_indexed,
            recredited_count=recredited,
            pending_count=pending,
            main_domain=p.main_domain,
            created_at=p.created_at,
        ))
    return summaries


@router.get("/stats/indexing", response_model=IndexingStatsResponse)
@limiter.limit("30/minute")
async def get_indexing_stats(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get indexing speed stats (24h/48h/72h/7d) and method success rates."""
    from sqlalchemy import case, extract

    # --- Speed stats via SQL aggregation ---
    hours_expr = extract(
        "epoch", URLModel.indexed_at - URLModel.submitted_at
    ) / 3600.0

    speed_result = await db.execute(
        select(
            func.count().label("total_submitted"),
            func.count().filter(hours_expr <= 24).label("idx_24h"),
            func.count().filter(hours_expr <= 48).label("idx_48h"),
            func.count().filter(hours_expr <= 72).label("idx_72h"),
            func.count().filter(hours_expr <= 168).label("idx_7d"),
        )
        .select_from(URLModel)
        .join(Project)
        .where(
            Project.user_id == user.id,
            URLModel.status != URLStatus.pending,
        )
    )
    row = speed_result.one()
    total_submitted = row.total_submitted or 0
    indexed_24h = row.idx_24h or 0
    indexed_48h = row.idx_48h or 0
    indexed_72h = row.idx_72h or 0
    indexed_7d = row.idx_7d or 0

    speed = IndexingSpeedStats(
        indexed_24h=indexed_24h,
        indexed_48h=indexed_48h,
        indexed_72h=indexed_72h,
        indexed_7d=indexed_7d,
        total_submitted=total_submitted,
        pct_24h=round(indexed_24h / total_submitted * 100, 1) if total_submitted else 0,
        pct_48h=round(indexed_48h / total_submitted * 100, 1) if total_submitted else 0,
        pct_72h=round(indexed_72h / total_submitted * 100, 1) if total_submitted else 0,
        pct_7d=round(indexed_7d / total_submitted * 100, 1) if total_submitted else 0,
    )

    # --- Method success rates via SQL aggregation ---
    log_result = await db.execute(
        select(
            IndexingLog.method,
            func.count().label("total"),
            func.count().filter(IndexingLog.status == "success").label("success_count"),
        )
        .join(URLModel, IndexingLog.url_id == URLModel.id)
        .join(Project, URLModel.project_id == Project.id)
        .where(Project.user_id == user.id)
        .group_by(IndexingLog.method)
    )

    methods: dict[str, MethodStats] = {}
    for row in log_result.all():
        total = row.total or 0
        success = row.success_count or 0
        error = total - success
        methods[row.method] = MethodStats(
            total_attempts=total,
            success=success,
            error=error,
            rate=round(success / total * 100, 1) if total else 0,
        )

    # Count URLs indexed by the service: confirmed not-indexed at least once, then indexed
    ibs_result = await db.execute(
        select(func.count(URLModel.id))
        .join(Project)
        .where(
            Project.user_id == user.id,
            URLModel.status == URLStatus.indexed,
            URLModel.verified_not_indexed == True,
        )
    )
    indexed_by_service = ibs_result.scalar() or 0

    return IndexingStatsResponse(speed=speed, methods=methods, indexed_by_service=indexed_by_service)


@router.get("/stats/daily")
@limiter.limit("30/minute")
async def get_daily_stats(
    request: Request,
    days: int = Query(default=30, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily submission/indexation stats for the current user."""
    from sqlalchemy import cast, Date

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)

    # Submitted per day (SQL aggregation)
    sub_result = await db.execute(
        select(
            cast(URLModel.submitted_at, Date).label("day"),
            func.count().label("cnt"),
        )
        .join(Project)
        .where(
            Project.user_id == user.id,
            URLModel.submitted_at != None,
            URLModel.submitted_at >= cutoff,
        )
        .group_by("day")
    )
    submitted_by_day = {str(r.day): r.cnt for r in sub_result.all()}

    # Indexed per day (SQL aggregation)
    idx_result = await db.execute(
        select(
            cast(URLModel.indexed_at, Date).label("day"),
            func.count().label("cnt"),
        )
        .join(Project)
        .where(
            Project.user_id == user.id,
            URLModel.indexed_at != None,
            URLModel.indexed_at >= cutoff,
        )
        .group_by("day")
    )
    indexed_by_day = {str(r.day): r.cnt for r in idx_result.all()}

    # Build complete date range
    data = []
    for i in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        data.append({
            "date": date,
            "submitted": submitted_by_day.get(date, 0),
            "indexed": indexed_by_day.get(date, 0),
        })

    return data


@router.get("/{project_id}", response_model=ProjectDetail)
@limiter.limit("60/minute")
async def get_project(
    request: Request,
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project detail."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectDetail(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        total_urls=project.total_urls,
        indexed_count=project.indexed_count,
        failed_count=project.failed_count,
        main_domain=project.main_domain,
        gsc_service_account_id=project.gsc_service_account_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


class ProjectUpdate(BaseModel):
    gsc_service_account_id: uuid.UUID | None = None


@router.patch("/{project_id}")
@limiter.limit("30/minute")
async def update_project(
    request: Request,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update project settings (e.g. GSC service account)."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate that the SA exists if provided
    if data.gsc_service_account_id is not None:
        sa_result = await db.execute(
            select(ServiceAccount).where(ServiceAccount.id == data.gsc_service_account_id)
        )
        if not sa_result.scalars().first():
            raise HTTPException(status_code=404, detail="Service account not found")

    project.gsc_service_account_id = data.gsc_service_account_id
    await db.commit()
    return {"ok": True, "gsc_service_account_id": str(data.gsc_service_account_id) if data.gsc_service_account_id else None}


@router.post("/{project_id}/urls", response_model=AddUrlsResponse)
@limiter.limit("10/minute")
async def add_urls(
    request: Request,
    project_id: uuid.UUID,
    data: AddUrls,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add URLs to an existing project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Deduplicate against existing project URLs
    existing_result = await db.execute(
        select(URL.url).where(URL.project_id == project.id)
    )
    existing_urls = set(existing_result.scalars().all())
    new_urls = [u for u in data.urls if u not in existing_urls]

    if not new_urls:
        return AddUrlsResponse(added=0, total_urls=project.total_urls, credits_debited=0)

    credit_service = CreditService(db)
    balance = await credit_service.get_balance(user.id)
    if balance < len(new_urls):
        raise HTTPException(status_code=402, detail="Insufficient credits")

    url_objects = []
    for url_str in new_urls:
        url_obj = URL(project_id=project.id, url=url_str)
        db.add(url_obj)
        url_objects.append(url_obj)
    await db.flush()

    await credit_service.debit_credits(user.id, [u.id for u in url_objects])

    project.total_urls += len(new_urls)
    if not project.main_domain:
        project.main_domain = _extract_main_domain(new_urls)

    from app.tasks.indexing_tasks import submit_urls_for_indexing

    submit_urls_for_indexing.delay(
        str(project.id), [str(u.id) for u in url_objects], None
    )

    await db.commit()

    return AddUrlsResponse(
        added=len(new_urls),
        total_urls=project.total_urls,
        credits_debited=len(new_urls),
    )


@router.get("/{project_id}/gsc-sitemaps", response_model=list[GscSitemapInfo])
@limiter.limit("10/minute")
async def get_gsc_sitemaps(
    request: Request,
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List sitemaps from Google Search Console for the project's domain."""
    result = await db.execute(
        select(Project)
        .options(joinedload(Project.gsc_service_account))
        .where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Determine GSC credentials: per-project SA or global
    if project.gsc_service_account:
        gsc_property = f"sc-domain:{project.main_domain}" if project.main_domain else ""
        sa_info = project.gsc_service_account.json_key_dict
    else:
        from app.config import get_global_gsc_credentials
        sa_info = get_global_gsc_credentials()
        gsc_property = settings.GSC_PROPERTY
        if not gsc_property or not sa_info:
            raise HTTPException(status_code=501, detail="GSC not configured")

    try:
        sitemaps = list_sitemaps(gsc_property, sa_info)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GSC API error: {e}")

    # Filter sitemaps by the project's domain
    if project.main_domain:
        sitemaps = [
            sm for sm in sitemaps
            if project.main_domain in sm.get("path", "")
        ]

    # Fallback: if GSC returned nothing, probe /sitemap-index.xml on the domain
    if not sitemaps and project.main_domain:
        discovered = await discover_sitemap_index(project.main_domain)
        if discovered:
            sitemaps = discovered

    # Check which sitemaps have already been imported (latest record per sitemap)
    imported_result = await db.execute(
        select(
            ImportedSitemap.sitemap_url,
            func.max(ImportedSitemap.urls_imported).label("urls_imported"),
            func.max(ImportedSitemap.imported_at).label("imported_at"),
        )
        .where(ImportedSitemap.project_id == project_id)
        .group_by(ImportedSitemap.sitemap_url)
    )
    imported_map = {row.sitemap_url: row for row in imported_result.all()}

    for sm in sitemaps:
        imp = imported_map.get(sm["path"])
        if imp:
            sm["imported"] = True
            sm["imported_urls"] = imp.urls_imported
            sm["imported_at"] = imp.imported_at.isoformat() if imp.imported_at else None
        else:
            sm["imported"] = False
            sm["imported_urls"] = 0
            sm["imported_at"] = None

    return sitemaps


@router.post("/{project_id}/import-gsc", response_model=GscImportResponse)
@limiter.limit("5/minute")
async def import_gsc_urls(
    request: Request,
    project_id: uuid.UUID,
    data: GscImportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import URLs from GSC sitemaps into the project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch URLs from all selected sitemaps
    all_urls: list[str] = []
    for sitemap_url in data.sitemap_urls:
        try:
            urls = await fetch_sitemap_urls(sitemap_url)
            all_urls.extend(urls)
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to fetch sitemap {sitemap_url}: {e}"
            )

    if not all_urls:
        raise HTTPException(status_code=400, detail="No URLs found in selected sitemaps")

    # Deduplicate fetched URLs
    unique_fetched = list(dict.fromkeys(all_urls))

    # Get existing URLs for this project
    existing_result = await db.execute(
        select(URL.url).where(URL.project_id == project.id)
    )
    existing_urls = set(existing_result.scalars().all())

    # Filter out duplicates
    new_urls = [u for u in unique_fetched if u not in existing_urls]
    duplicates_skipped = len(unique_fetched) - len(new_urls)

    if not new_urls:
        # Still record the import even if all URLs are duplicates
        for sitemap_url in data.sitemap_urls:
            db.add(ImportedSitemap(
                project_id=project.id, sitemap_url=sitemap_url, urls_imported=0,
            ))
        await db.commit()
        return GscImportResponse(added=0, duplicates_skipped=duplicates_skipped, credits_debited=0)

    # Check credits
    credit_service = CreditService(db)
    balance = await credit_service.get_balance(user.id)
    if balance < len(new_urls):
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Balance: {balance}, required: {len(new_urls)}",
        )

    # Create URL entries
    url_objects = []
    for url_str in new_urls:
        url_obj = URL(project_id=project.id, url=url_str)
        db.add(url_obj)
        url_objects.append(url_obj)
    await db.flush()

    # Debit credits
    try:
        await credit_service.debit_credits(user.id, [u.id for u in url_objects])
    except InsufficientCreditsError:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    # Update project
    project.total_urls += len(new_urls)
    if not project.main_domain:
        project.main_domain = _extract_main_domain(new_urls)

    # Record imported sitemaps
    for sitemap_url in data.sitemap_urls:
        imp = ImportedSitemap(
            project_id=project.id,
            sitemap_url=sitemap_url,
            urls_imported=len(new_urls),
        )
        db.add(imp)

    # Queue indexing tasks
    from app.tasks.indexing_tasks import submit_urls_for_indexing

    submit_urls_for_indexing.delay(
        str(project.id), [str(u.id) for u in url_objects], None
    )

    await db.commit()

    return GscImportResponse(
        added=len(new_urls),
        duplicates_skipped=duplicates_skipped,
        credits_debited=len(new_urls),
    )


@router.get("/{project_id}/status", response_model=ProjectStatusSchema)
@limiter.limit("60/minute")
async def get_project_status(
    request: Request,
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str = Query(default="all", alias="status"),
    search: str = Query(default=""),
):
    """Get detailed project status with paginated URLs."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user.id)
    )
    if not proj_result.scalars().first():
        raise HTTPException(status_code=404, detail="Project not found")

    # Compute counts via SQL (fast, no need to load all URLs)
    count_result = await db.execute(
        select(URL.status, func.count(URL.id))
        .where(URL.project_id == project_id)
        .group_by(URL.status)
    )
    counts: dict[str, int] = {}
    for row in count_result.all():
        counts[row[0] if isinstance(row[0], str) else row[0].value] = row[1]

    total = sum(counts.values())
    indexed = counts.get("indexed", 0)
    verifying = counts.get("verifying", 0)
    pending = sum(counts.get(s, 0) for s in ("pending", "submitted", "indexing"))
    not_indexed = counts.get("not_indexed", 0)
    recredited = counts.get("recredited", 0)
    success_rate = (indexed / total * 100) if total > 0 else 0.0

    # Count URLs indexed by the service: confirmed not-indexed at least once, then indexed
    ibs_result = await db.execute(
        select(func.count(URL.id)).where(
            URL.project_id == project_id,
            URL.status == URLStatus.indexed,
            URL.verified_not_indexed == True,
        )
    )
    indexed_by_service = ibs_result.scalar() or 0

    # Build paginated URL query with optional filters
    url_query = select(URL).where(URL.project_id == project_id)

    if status_filter != "all":
        url_query = url_query.where(URL.status == status_filter)

    if search:
        url_query = url_query.where(URL.url.ilike(f"%{search}%"))

    # Count matching URLs for pagination info
    count_q = select(func.count(URL.id)).where(URL.project_id == project_id)
    if status_filter != "all":
        count_q = count_q.where(URL.status == status_filter)
    if search:
        count_q = count_q.where(URL.url.ilike(f"%{search}%"))
    urls_total_result = await db.execute(count_q)
    urls_total = urls_total_result.scalar() or 0

    # Fetch paginated URLs
    url_query = url_query.order_by(URL.created_at.desc()).offset(offset).limit(limit)
    urls_result = await db.execute(url_query)
    urls = urls_result.scalars().all()

    return ProjectStatusSchema(
        total=total,
        indexed=indexed,
        pending=pending,
        not_indexed=not_indexed,
        recredited=recredited,
        verifying=verifying,
        indexed_by_service=indexed_by_service,
        success_rate=round(success_rate, 1),
        urls=urls,
        urls_total=urls_total,
        limit=limit,
        offset=offset,
    )


@router.post("/{project_id}/verify-now")
@limiter.limit("5/minute")
async def verify_now(
    request: Request,
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger immediate verification for a project's pending URLs."""
    proj_result = await db.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user.id)
    )
    if not proj_result.scalars().first():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(URL.id).where(
            URL.project_id == project_id,
            URL.status.in_([URLStatus.submitted, URLStatus.indexing, URLStatus.verifying]),
        )
    )
    url_ids = [str(uid) for uid in result.scalars().all()]

    if url_ids:
        from app.tasks.verification_tasks import verify_project_urls
        verify_project_urls.delay(str(project_id), url_ids)

    return {"queued": len(url_ids)}


@router.get("/{project_id}/export/csv")
@limiter.limit("10/minute")
async def export_project_csv(
    request: Request,
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export project URLs and their status as CSV."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.urls))
        .where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "url", "status", "is_indexed", "indexed_at",
        "google_api_attempts", "indexnow_attempts",
        "sitemap_ping_attempts", "social_signal_attempts",
        "backlink_ping_attempts", "check_count", "check_method",
        "indexed_title", "indexed_snippet",
        "submitted_at", "created_at",
    ])

    for u in project.urls:
        writer.writerow([
            u.url, u.status, u.is_indexed,
            u.indexed_at.isoformat() if u.indexed_at else "",
            u.google_api_attempts, u.indexnow_attempts,
            u.sitemap_ping_attempts, u.social_signal_attempts,
            u.backlink_ping_attempts, u.check_count,
            u.check_method or "",
            u.indexed_title or "", u.indexed_snippet or "",
            u.submitted_at.isoformat() if u.submitted_at else "",
            u.created_at.isoformat(),
        ])

    output.seek(0)
    safe_name = project.name.replace(" ", "_")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_urls.csv"'},
    )
