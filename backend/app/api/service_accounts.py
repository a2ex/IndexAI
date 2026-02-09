import uuid
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.auth import get_current_user
from app.rate_limit import limiter
from app.models.user import User
from app.models.service_account import ServiceAccount

router = APIRouter(prefix="/api/service-accounts", tags=["service-accounts"])


class ServiceAccountSummary(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ServiceAccountSummary])
@limiter.limit("30/minute")
async def list_service_accounts(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active service accounts (for GSC configuration dropdown)."""
    result = await db.execute(
        select(ServiceAccount).where(ServiceAccount.is_active == True).order_by(ServiceAccount.name)
    )
    return result.scalars().all()
