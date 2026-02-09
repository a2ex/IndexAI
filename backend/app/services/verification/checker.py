import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.services.verification.custom_search import check_indexed_custom_search
from app.services.verification.gsc_inspection import check_indexed_gsc_inspection
from app.services.verification.fallback_check import check_indexed_fallback

logger = logging.getLogger(__name__)


class IndexationChecker:
    """
    Orchestrates the 3 verification methods.
    Priority: GSC Inspection > Custom Search > Fallback.
    """

    def __init__(self, config: dict):
        self.config = config

    async def check_url(self, url: str) -> dict:
        """Check indexation of a URL with the best available method."""

        # Priority method: GSC Inspection (if site owner)
        if self.config.get("gsc_property") and self.config.get("service_account_info"):
            try:
                result = check_indexed_gsc_inspection(
                    url,
                    self.config["gsc_property"],
                    self.config["service_account_info"],
                )
                if result["is_indexed"] is not None:
                    return result
            except Exception as e:
                logger.error(f"GSC inspection failed for {url}: {e}")

        # Fallback: Custom Search API
        if self.config.get("custom_search_api_key") and self.config.get("cse_id"):
            try:
                result = check_indexed_custom_search(
                    url,
                    self.config["custom_search_api_key"],
                    self.config["cse_id"],
                )
                if result["is_indexed"] is not None:
                    return result
            except Exception as e:
                logger.error(f"Custom Search check failed for {url}: {e}")

        # Last resort: direct verification
        return await check_indexed_fallback(url)


async def build_checker_for_project(db: AsyncSession, project_id: str | UUID) -> IndexationChecker:
    """Build an IndexationChecker using the project's GSC service account if configured,
    otherwise fall back to global settings."""
    from app.config import settings
    from app.models.project import Project

    result = await db.execute(
        select(Project)
        .options(joinedload(Project.gsc_service_account))
        .where(Project.id == project_id)
    )
    project = result.scalars().first()

    if project and project.gsc_service_account:
        sa = project.gsc_service_account
        return IndexationChecker({
            "gsc_property": "auto",  # _match_gsc_property will auto-detect
            "service_account_info": sa.json_key_dict,
            "custom_search_api_key": settings.GOOGLE_CUSTOM_SEARCH_API_KEY,
            "cse_id": settings.GOOGLE_CSE_ID,
        })

    # Fallback to global settings
    from app.config import get_global_gsc_credentials
    global_creds = get_global_gsc_credentials()
    return IndexationChecker({
        "gsc_property": settings.GSC_PROPERTY or "auto",
        "service_account_info": global_creds,
        "custom_search_api_key": settings.GOOGLE_CUSTOM_SEARCH_API_KEY,
        "cse_id": settings.GOOGLE_CSE_ID,
    })
