import logging
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
        if self.config.get("gsc_property") and self.config.get("service_account_json"):
            try:
                result = check_indexed_gsc_inspection(
                    url,
                    self.config["gsc_property"],
                    self.config["service_account_json"],
                )
                if result["is_indexed"] is not None:
                    return result
            except Exception as e:
                logger.error(f"GSC inspection failed: {e}")

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
                logger.error(f"Custom search check failed: {e}")

        # Last resort: direct verification
        return await check_indexed_fallback(url)
