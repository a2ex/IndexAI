import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, delete as sa_delete, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.auth import get_current_user
from app.rate_limit import limiter
from app.models.user import User
from app.models.url import URL, URLStatus
from app.models.project import Project
from app.models.credit import CreditTransaction, TransactionType
from app.models.indexing_log import IndexingLog
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


@router.post("/{url_id}/check")
@limiter.limit("10/minute")
async def check_url(
    request: Request,
    url_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force an immediate indexation check for a URL."""
    result = await db.execute(
        select(URL)
        .join(Project)
        .where(URL.id == url_id, Project.user_id == user.id)
    )
    url_obj = result.scalars().first()
    if not url_obj:
        raise HTTPException(status_code=404, detail="URL not found")

    from app.tasks.verification_tasks import check_single_url

    check_single_url.delay(str(url_id))

    return {"message": "Verification launched", "url_id": str(url_id)}


@router.delete("/{url_id}")
@limiter.limit("30/minute")
async def delete_url(
    request: Request,
    url_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a URL from the project and refund the credit if it was debited."""
    result = await db.execute(
        select(URL)
        .join(Project)
        .where(URL.id == url_id, Project.user_id == user.id)
    )
    url_obj = result.scalars().first()
    if not url_obj:
        raise HTTPException(status_code=404, detail="URL not found")

    refunded = False
    if url_obj.credit_debited and not url_obj.credit_refunded:
        user.credit_balance += 1
        url_obj.credit_refunded = True
        db.add(CreditTransaction(
            user_id=user.id,
            amount=1,
            type=TransactionType.refund,
            description="URL removed from project",
            url_id=url_obj.id,
        ))
        refunded = True

    # Clean up related records before deleting the URL
    await db.execute(sa_delete(IndexingLog).where(IndexingLog.url_id == url_obj.id))
    await db.execute(
        sa_update(CreditTransaction)
        .where(CreditTransaction.url_id == url_obj.id)
        .values(url_id=None)
    )

    # Update project total_urls
    proj_result = await db.execute(select(Project).where(Project.id == url_obj.project_id))
    project = proj_result.scalars().first()
    if project and project.total_urls > 0:
        project.total_urls -= 1

    await db.delete(url_obj)
    await db.commit()

    return {"message": "URL deleted", "url_id": str(url_id), "credit_refunded": refunded}
