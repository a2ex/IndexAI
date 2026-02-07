import logging
import httpx

logger = logging.getLogger(__name__)


async def check_indexed_fallback(url: str) -> dict:
    """
    Fallback: search for the exact URL in Google.
    Uses the URL in quotes for an exact match search.
    CAUTION: Least reliable method, can be rate-limited by Google.
    """
    search_url = f"https://www.google.com/search?q=%22{url}%22&num=1"

    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        follow_redirects=True,
        timeout=10,
    ) as client:
        try:
            response = await client.get(search_url)
            is_indexed = url.lower() in response.text.lower()

            return {
                "is_indexed": is_indexed,
                "method": "fallback",
                "note": "Low confidence - use other methods for reliable results",
            }
        except Exception as e:
            logger.error(f"Fallback check failed for {url}: {e}")
            return {
                "is_indexed": None,
                "error": str(e),
                "method": "fallback",
            }
