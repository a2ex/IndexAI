import logging
from urllib.parse import urlparse
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def ping_backlink_trackers(url: str) -> list[dict]:
    """
    Ping backlink tracking and web crawling services.
    These services crawl the web regularly, and by signaling a URL,
    we increase the chances that Googlebot discovers it too.
    """
    results = []

    # 1. WebSub / PubSubHubbub (proper POST)
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                "https://pubsubhubbub.appspot.com/",
                data={"hub.mode": "publish", "hub.url": url},
            )
            results.append({
                "service": "pubsubhubbub",
                "status": resp.status_code,
                "success": resp.status_code < 400,
            })
        except Exception as e:
            results.append({"service": "pubsubhubbub", "error": str(e), "success": False})

    # 2 & 3. IndexNow pings to Bing & Yandex (with API key)
    api_key = settings.INDEXNOW_API_KEY
    if api_key:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        for engine, endpoint in [("bing", "https://www.bing.com/indexnow"), ("yandex", "https://yandex.com/indexnow")]:
            async with httpx.AsyncClient(timeout=15) as client:
                try:
                    resp = await client.get(
                        endpoint,
                        params={"url": url, "key": api_key},
                        follow_redirects=True,
                    )
                    results.append({
                        "service": f"{engine}_indexnow_direct",
                        "status": resp.status_code,
                        "success": resp.status_code < 400,
                    })
                except Exception as e:
                    results.append({"service": f"{engine}_indexnow_direct", "error": str(e), "success": False})
    else:
        logger.warning("INDEXNOW_API_KEY not configured, skipping IndexNow pings")

    logger.info(f"Backlink pings for {url}: {len(results)} services pinged")
    return results
