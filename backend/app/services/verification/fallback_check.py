import logging

logger = logging.getLogger(__name__)


async def check_indexed_fallback(url: str) -> dict:
    """
    Fallback method — disabled.
    Google scraping produces false positives (the searched URL always appears
    in the HTML even when there are no actual results), so we return
    is_indexed=None to avoid marking URLs as indexed incorrectly.
    """
    logger.warning(
        f"No reliable indexation check method available for {url}. "
        "Configure GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CSE_ID for accurate results."
    )
    return {
        "is_indexed": None,
        "method": "fallback",
        "note": "Fallback disabled — no reliable check method configured",
    }
