import logging
import httpx

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

    # 2. IndexNow direct ping to Bing (as a backlink signal)
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"https://www.bing.com/indexnow?url={url}",
                follow_redirects=True,
            )
            results.append({
                "service": "bing_indexnow_direct",
                "status": resp.status_code,
                "success": resp.status_code < 400,
            })
        except Exception as e:
            results.append({"service": "bing_indexnow_direct", "error": str(e), "success": False})

    # 3. Yandex direct ping
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"https://yandex.com/indexnow?url={url}",
                follow_redirects=True,
            )
            results.append({
                "service": "yandex_indexnow_direct",
                "status": resp.status_code,
                "success": resp.status_code < 400,
            })
        except Exception as e:
            results.append({"service": "yandex_indexnow_direct", "error": str(e), "success": False})

    logger.info(f"Backlink pings for {url}: {len(results)} services pinged")
    return results
