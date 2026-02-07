import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.auth import get_current_user
from app.rate_limit import limiter
from app.models.user import User
from app.models.credit import CreditTransaction
from app.schemas.credit import CreditBalance, CreditTransactionResponse
from app.services.credits import CreditService

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("", response_model=CreditBalance)
@limiter.limit("60/minute")
async def get_credits(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get credit balance."""
    return CreditBalance(balance=user.credit_balance, user_id=user.id)


@router.get("/history", response_model=list[CreditTransactionResponse])
@limiter.limit("60/minute")
async def get_credit_history(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Get credit transaction history."""
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .order_by(CreditTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/add")
@limiter.limit("10/minute")
async def add_credits(
    request: Request,
    amount: int = Query(gt=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add credits to the user's balance (admin/testing endpoint)."""
    credit_service = CreditService(db)
    new_balance = await credit_service.add_credits(user.id, amount)
    await db.commit()
    return {"balance": new_balance, "added": amount}
