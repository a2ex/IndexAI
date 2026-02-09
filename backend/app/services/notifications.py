import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.url import URL
from app.models.project import Project
from app.models.notification import NotificationSettings

logger = logging.getLogger(__name__)


async def send_webhook(webhook_url: str, payload: dict) -> bool:
    """POST JSON payload to a webhook URL. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"Webhook sent to {webhook_url} — status {response.status_code}")
            return True
    except Exception as e:
        logger.error(f"Webhook failed for {webhook_url}: {e}")
        return False


def send_email_digest(to_email: str, urls_indexed: list[dict]) -> bool:
    """Send an HTML email digest of recently indexed URLs."""
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured, skipping email digest")
        return False

    subject = f"IndexAI — {len(urls_indexed)} URL(s) indexed today"

    rows = ""
    for u in urls_indexed:
        rows += f"<tr><td style='padding:6px 12px;border-bottom:1px solid #eee'><a href='{u['url']}'>{u['url']}</a></td>"
        rows += f"<td style='padding:6px 12px;border-bottom:1px solid #eee'>{u.get('project', '—')}</td>"
        rows += f"<td style='padding:6px 12px;border-bottom:1px solid #eee'>{u.get('indexed_at', '—')}</td></tr>"

    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
        <h2 style="color:#1a1a1a">IndexAI Daily Digest</h2>
        <p style="color:#555">{len(urls_indexed)} URL(s) indexed in the last 24 hours.</p>
        <table style="width:100%;border-collapse:collapse;font-size:14px">
            <thead>
                <tr style="background:#f5f5f5">
                    <th style="padding:8px 12px;text-align:left">URL</th>
                    <th style="padding:8px 12px;text-align:left">Project</th>
                    <th style="padding:8px 12px;text-align:left">Indexed at</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p style="color:#999;font-size:12px;margin-top:20px">
            You receive this email because email digest is enabled in your IndexAI settings.
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        logger.info(f"Email digest sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email digest failed for {to_email}: {e}")
        return False


async def notify_url_indexed(db: AsyncSession, url_obj: URL) -> None:
    """Called when a URL is marked as indexed. Sends webhook if configured."""
    try:
        # Load the project and its user's notification settings
        result = await db.execute(
            select(Project).where(Project.id == url_obj.project_id)
        )
        project = result.scalars().first()
        if not project:
            return

        result = await db.execute(
            select(NotificationSettings).where(NotificationSettings.user_id == project.user_id)
        )
        notif_settings = result.scalars().first()
        if not notif_settings:
            return

        payload = {
            "event": "url.indexed",
            "url": url_obj.url,
            "indexed_at": (url_obj.indexed_at or datetime.now(timezone.utc).replace(tzinfo=None)).isoformat(),
            "project_id": str(project.id),
            "project_name": project.name,
            "title": url_obj.indexed_title,
            "snippet": url_obj.indexed_snippet,
        }

        if notif_settings.webhook_enabled and notif_settings.webhook_url:
            await send_webhook(notif_settings.webhook_url, payload)

    except Exception as e:
        logger.error(f"notify_url_indexed failed: {e}")
