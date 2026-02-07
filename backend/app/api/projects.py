import csv
import io
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.api.auth import get_current_user
from app.rate_limit import limiter
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.url import URL, URLStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectSummary,
    ProjectDetail,
    ProjectStatus as ProjectStatusSchema,
    AddUrls,
    AddUrlsResponse,
)
from app.services.credits import CreditService, InsufficientCreditsError

from app.models.url import URL as URLModel, URLStatus

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
    """List all projects for the current user."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user.id)
        .order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectDetail)
@limiter.limit("60/minute")
async def get_project(
    request: Request,
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project detail with all URL statuses."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.urls))
        .where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


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

    credit_service = CreditService(db)
    balance = await credit_service.get_balance(user.id)
    if balance < len(data.urls):
        raise HTTPException(status_code=402, detail="Insufficient credits")

    url_objects = []
    for url_str in data.urls:
        url_obj = URL(project_id=project.id, url=url_str)
        db.add(url_obj)
        url_objects.append(url_obj)
    await db.flush()

    await credit_service.debit_credits(user.id, [u.id for u in url_objects])

    project.total_urls += len(data.urls)

    from app.tasks.indexing_tasks import submit_urls_for_indexing

    submit_urls_for_indexing.delay(
        str(project.id), [str(u.id) for u in url_objects], None
    )

    await db.commit()

    return AddUrlsResponse(
        added=len(data.urls),
        total_urls=project.total_urls,
        credits_debited=len(data.urls),
    )


@router.get("/{project_id}/status", response_model=ProjectStatusSchema)
@limiter.limit("60/minute")
async def get_project_status(
    request: Request,
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed project status."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.urls))
        .where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    urls = project.urls
    total = len(urls)
    indexed = sum(1 for u in urls if u.status == URLStatus.indexed)
    pending = sum(1 for u in urls if u.status in [URLStatus.pending, URLStatus.submitted, URLStatus.indexing])
    not_indexed = sum(1 for u in urls if u.status == URLStatus.not_indexed)
    recredited = sum(1 for u in urls if u.status == URLStatus.recredited)
    success_rate = (indexed / total * 100) if total > 0 else 0.0

    return ProjectStatusSchema(
        total=total,
        indexed=indexed,
        pending=pending,
        not_indexed=not_indexed,
        recredited=recredited,
        success_rate=round(success_rate, 1),
        urls=urls,
    )


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


@router.get("/stats/daily")
@limiter.limit("30/minute")
async def get_daily_stats(
    request: Request,
    days: int = Query(default=30, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily submission/indexation stats for the current user."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get all URLs for the user's projects
    result = await db.execute(
        select(URLModel)
        .join(Project)
        .where(Project.user_id == user.id, URLModel.created_at >= cutoff)
    )
    urls = result.scalars().all()

    # Build daily stats
    submitted_by_day: dict[str, int] = defaultdict(int)
    indexed_by_day: dict[str, int] = defaultdict(int)

    for u in urls:
        if u.submitted_at:
            day = u.submitted_at.strftime("%Y-%m-%d")
            submitted_by_day[day] += 1
        if u.indexed_at:
            day = u.indexed_at.strftime("%Y-%m-%d")
            indexed_by_day[day] += 1

    # Build complete date range
    data = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        data.append({
            "date": date,
            "submitted": submitted_by_day.get(date, 0),
            "indexed": indexed_by_day.get(date, 0),
        })

    return data
