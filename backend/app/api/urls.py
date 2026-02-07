import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.auth import get_current_user
from app.rate_limit import limiter
from app.models.user import User
from app.models.url import URL
from app.models.project import Project
from app.schemas.url import URLResponse

router = APIRouter(prefix="/api/urls", tags=["urls"])


@router.get("/{url_id}", response_model=URLResponse)
@limiter.limit("60/minute")
async def get_url(
    request: Request,
    url_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of a single URL."""
    result = await db.execute(
        select(URL)
        .join(Project)
        .where(URL.id == url_id, Project.user_id == user.id)
    )
    url_obj = result.scalars().first()
    if not url_obj:
        raise HTTPException(status_code=404, detail="URL not found")
    return url_obj


@router.post("/{url_id}/resubmit")
@limiter.limit("20/minute")
async def resubmit_url(
    request: Request,
    url_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-submit a URL for indexation (no additional credit charge)."""
    result = await db.execute(
        select(URL)
        .join(Project)
        .where(URL.id == url_id, Project.user_id == user.id)
    )
    url_obj = result.scalars().first()
    if not url_obj:
        raise HTTPException(status_code=404, detail="URL not found")

    url_obj.status = "submitted"

    from app.tasks.indexing_tasks import submit_single_url_task

    submit_single_url_task.delay(str(url_id))

    await db.commit()
    return {"message": "URL resubmitted for indexation", "url_id": str(url_id)}
