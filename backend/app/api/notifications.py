from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.auth import get_current_user
from app.rate_limit import limiter
from app.models.user import User
from app.models.project import Project
from app.models.url import URL, URLStatus

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/recent")
@limiter.limit("60/minute")
async def get_recent_indexed(
    request: Request,
    since: str = Query(default=""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return URLs indexed recently for the current user."""
    # Get user's projects
    result = await db.execute(
        select(Project.id).where(Project.user_id == user.id)
    )
    project_ids = [row[0] for row in result.all()]
    if not project_ids:
        return []

    # Parse since timestamp, default to last 2 hours
    cutoff = datetime.utcnow() - timedelta(hours=2)
    if since:
        try:
            cutoff = datetime.fromisoformat(since)
        except ValueError:
            pass

    result = await db.execute(
        select(URL).where(
            and_(
                URL.project_id.in_(project_ids),
                URL.status == URLStatus.indexed,
                URL.indexed_at >= cutoff,
            )
        ).order_by(URL.indexed_at.desc()).limit(50)
    )
    urls = result.scalars().all()

    return [
        {
            "id": str(u.id),
            "url": u.url,
            "indexed_at": u.indexed_at.isoformat() if u.indexed_at else None,
            "title": u.indexed_title,
        }
        for u in urls
    ]
