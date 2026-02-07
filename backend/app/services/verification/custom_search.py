import logging
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def check_indexed_custom_search(url: str, api_key: str, cse_id: str) -> dict:
    """
    Check if a URL is indexed via Google Custom Search API.
    Query site:URL and check if results exist.
    Quota: 100 free queries/day. 10,000/day with billing ($5/1000 queries).
    """
    service = build("customsearch", "v1", developerKey=api_key)

    try:
        result = service.cse().list(q=f"site:{url}", cx=cse_id).execute()

        is_indexed = "items" in result and len(result["items"]) > 0

        title = None
        snippet = None
        if is_indexed and result["items"]:
            title = result["items"][0].get("title")
            snippet = result["items"][0].get("snippet")

        return {
            "is_indexed": is_indexed,
            "title": title,
            "snippet": snippet,
            "method": "custom_search",
            "total_results": int(
                result.get("searchInformation", {}).get("totalResults", 0)
            ),
        }

    except Exception as e:
        logger.error(f"Custom Search check failed for {url}: {e}")
        return {
            "is_indexed": None,
            "error": str(e),
            "method": "custom_search",
        }
