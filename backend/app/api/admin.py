import uuid
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.auth import get_admin_user
from app.rate_limit import limiter
from app.models.user import User
from app.models.service_account import ServiceAccount
from app.models.notification import NotificationSettings
from app.schemas.notification import NotificationSettingsResponse, NotificationSettingsUpdate
from app.services.notifications import send_webhook
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/service-accounts")
@limiter.limit("30/minute")
async def list_service_accounts(
    request: Request,
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all registered service accounts."""
    result = await db.execute(
        select(ServiceAccount).order_by(ServiceAccount.created_at.desc())
    )
    accounts = result.scalars().all()
    return [
        {
            "id": str(sa.id),
            "name": sa.name,
            "email": sa.email,
            "daily_quota": sa.daily_quota,
            "used_today": sa.used_today,
            "is_active": sa.is_active,
            "created_at": sa.created_at.isoformat(),
        }
        for sa in accounts
    ]


@router.post("/service-accounts")
@limiter.limit("10/minute")
async def add_service_account(
    request: Request,
    name: str = Form(...),
    json_key: UploadFile = File(...),
    daily_quota: int = Form(default=200),
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a service account JSON key and register it."""
    content = await json_key.read()
    try:
        key_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    email = key_data.get("client_email")
    if not email:
        raise HTTPException(status_code=400, detail="No client_email found in JSON key")

    # Save the key file
    creds_dir = Path(settings.CREDENTIALS_DIR)
    creds_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace(" ", "_").lower()
    key_path = creds_dir / f"{safe_name}.json"
    key_path.write_bytes(content)

    # Check if already registered
    existing = await db.execute(
        select(ServiceAccount).where(ServiceAccount.email == email)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail=f"Service account {email} already registered")

    sa = ServiceAccount(
        name=name,
        email=email,
        json_key_path=str(key_path),
        daily_quota=daily_quota,
        is_active=True,
    )
    db.add(sa)
    await db.commit()
    await db.refresh(sa)

    return {
        "id": str(sa.id),
        "name": sa.name,
        "email": sa.email,
        "daily_quota": sa.daily_quota,
        "message": f"Service account {email} registered successfully",
    }


@router.delete("/service-accounts/{sa_id}")
@limiter.limit("10/minute")
async def delete_service_account(
    request: Request,
    sa_id: uuid.UUID,
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a service account."""
    result = await db.execute(select(ServiceAccount).where(ServiceAccount.id == sa_id))
    sa = result.scalars().first()
    if not sa:
        raise HTTPException(status_code=404, detail="Service account not found")

    # Delete key file
    key_path = Path(sa.json_key_path)
    if key_path.exists():
        key_path.unlink()

    await db.delete(sa)
    await db.commit()
    return {"message": f"Service account {sa.email} deleted"}


@router.post("/service-accounts/{sa_id}/test")
@limiter.limit("10/minute")
async def test_service_account(
    request: Request,
    sa_id: uuid.UUID,
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Test that a service account can authenticate with Google."""
    result = await db.execute(select(ServiceAccount).where(ServiceAccount.id == sa_id))
    sa = result.scalars().first()
    if not sa:
        raise HTTPException(status_code=404, detail="Service account not found")

    try:
        from oauth2client.service_account import ServiceAccountCredentials
        import httplib2

        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            sa.json_key_path,
            scopes=["https://www.googleapis.com/auth/indexing"],
        )
        http = credentials.authorize(httplib2.Http())
        # Just test authentication, don't submit anything
        response, _ = http.request(
            "https://indexing.googleapis.com/v3/urlNotifications/metadata?url=https://example.com",
            method="GET",
        )
        status = int(response["status"])
        return {
            "success": status != 401,
            "status_code": status,
            "message": "Authentication OK" if status != 401 else "Authentication failed",
            "email": sa.email,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "email": sa.email,
        }


@router.get("/settings")
@limiter.limit("30/minute")
async def get_settings(request: Request, user: User = Depends(get_admin_user)):
    """Get current Google API settings (redacted)."""
    return {
        "google_custom_search_api_key": "***" + settings.GOOGLE_CUSTOM_SEARCH_API_KEY[-8:] if len(settings.GOOGLE_CUSTOM_SEARCH_API_KEY) > 8 else "(not set)",
        "google_cse_id": settings.GOOGLE_CSE_ID or "(not set)",
        "credentials_dir": settings.CREDENTIALS_DIR,
        "base_url": settings.BASE_URL,
    }


@router.post("/settings")
@limiter.limit("10/minute")
async def update_settings(
    request: Request,
    google_custom_search_api_key: str = Form(default=""),
    google_cse_id: str = Form(default=""),
    user: User = Depends(get_admin_user),
):
    """
    Update Google API settings.
    Note: This updates the in-memory settings only. For persistence, update .env file.
    """
    updated = []
    if google_custom_search_api_key:
        settings.GOOGLE_CUSTOM_SEARCH_API_KEY = google_custom_search_api_key
        updated.append("GOOGLE_CUSTOM_SEARCH_API_KEY")
    if google_cse_id:
        settings.GOOGLE_CSE_ID = google_cse_id
        updated.append("GOOGLE_CSE_ID")

    return {"updated": updated, "message": "Settings updated (in-memory only, update .env for persistence)"}


@router.get("/notifications", response_model=NotificationSettingsResponse)
@limiter.limit("30/minute")
async def get_notification_settings(
    request: Request,
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification settings for the current user."""
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == user.id)
    )
    notif = result.scalars().first()
    if not notif:
        return NotificationSettingsResponse()
    return notif


@router.post("/notifications", response_model=NotificationSettingsResponse)
@limiter.limit("10/minute")
async def update_notification_settings(
    request: Request,
    payload: NotificationSettingsUpdate,
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update notification settings for the current user."""
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == user.id)
    )
    notif = result.scalars().first()

    if notif:
        notif.webhook_url = payload.webhook_url
        notif.webhook_enabled = payload.webhook_enabled
        notif.email_digest_enabled = payload.email_digest_enabled
        notif.email_digest_address = payload.email_digest_address
    else:
        notif = NotificationSettings(
            user_id=user.id,
            webhook_url=payload.webhook_url,
            webhook_enabled=payload.webhook_enabled,
            email_digest_enabled=payload.email_digest_enabled,
            email_digest_address=payload.email_digest_address,
        )
        db.add(notif)

    await db.commit()
    await db.refresh(notif)
    return notif


@router.post("/notifications/test-webhook")
@limiter.limit("5/minute")
async def test_webhook(
    request: Request,
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test payload to the configured webhook URL."""
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == user.id)
    )
    notif = result.scalars().first()

    if not notif or not notif.webhook_url:
        raise HTTPException(status_code=400, detail="No webhook URL configured")

    payload = {
        "event": "webhook.test",
        "message": "This is a test webhook from IndexAI",
        "user_email": user.email,
    }

    success = await send_webhook(notif.webhook_url, payload)
    return {
        "success": success,
        "webhook_url": notif.webhook_url,
        "message": "Test webhook sent successfully" if success else "Webhook delivery failed",
    }
