import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.rate_limit import limiter
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserResponse)
@limiter.limit("5/minute")
async def create_user(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user and generate an API key."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="Email already registered")

    api_key = f"idx_{secrets.token_urlsafe(32)}"
    user = User(email=data.email, api_key=api_key, credit_balance=100)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
