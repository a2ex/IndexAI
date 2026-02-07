import logging
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)


async def ping_web_services(url: str) -> list[dict]:
    """Ping web services to create crawl signals."""
    results = []

    # 1. Ping-O-Matic (notifies multiple services at once including Google Blog Search,
    #    Weblogs.com, Feed Burner, etc.)
    pingomatic_url = "http://rpc.pingomatic.com/"
    xml_body = f"""<?xml version="1.0"?>
    <methodCall>
        <methodName>weblogUpdates.ping</methodName>
        <params>
            <param><value>URL Update</value></param>
            <param><value>{url}</value></param>
        </params>
    </methodCall>"""

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(
                pingomatic_url,
                content=xml_body,
                headers={"Content-Type": "text/xml"},
            )
            results.append({"service": "pingomatic", "status": resp.status_code, "success": resp.status_code < 400})
        except Exception as e:
            results.append({"service": "pingomatic", "error": str(e), "success": False})

    # 2. WebSub (PubSubHubbub) — notify hubs about content updates
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(
                "https://pubsubhubbub.appspot.com/",
                data={"hub.mode": "publish", "hub.url": url},
            )
            results.append({
                "service": "websub",
                "status": resp.status_code,
                "success": resp.status_code < 400,
            })
        except Exception as e:
            results.append({"service": "websub", "error": str(e), "success": False})

    # 3. Internet Archive — save a snapshot (triggers a crawl)
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"https://web.archive.org/save/{url}",
                follow_redirects=True,
            )
            results.append({
                "service": "archive_org",
                "status": resp.status_code,
                "success": resp.status_code < 400,
            })
        except Exception as e:
            results.append({"service": "archive_org", "error": str(e), "success": False})

    logger.info(f"Social signals for {url}: {len(results)} services pinged")
    return results


def generate_rss_feed(urls: list[str], feed_url: str) -> str:
    """Generate an RSS feed containing URLs to trigger crawls."""
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = ""
    for url in urls:
        items += f"""
        <item>
            <title>Page Update</title>
            <link>{url}</link>
            <pubDate>{now}</pubDate>
            <guid isPermaLink="true">{url}</guid>
        </item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Indexing Feed</title>
            <link>{feed_url}</link>
            <description>URLs for indexing</description>
            <lastBuildDate>{now}</lastBuildDate>
            {items}
        </channel>
    </rss>"""

    return rss
