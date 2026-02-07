import logging
import httpx

logger = logging.getLogger(__name__)

INDEXNOW_ENDPOINTS = {
    "bing": "https://www.bing.com/indexnow",
    "yandex": "https://yandex.com/indexnow",
    "indexnow_org": "https://api.indexnow.org/indexnow",
}


async def submit_indexnow(
    urls: list[str],
    host: str,
    api_key: str,
    key_location: str,
    engine: str = "bing",
) -> dict:
    """
    Submit URLs via IndexNow protocol.
    URLs submitted to one engine are automatically shared with all participants.
    """
    endpoint = INDEXNOW_ENDPOINTS.get(engine, INDEXNOW_ENDPOINTS["bing"])

    payload = {
        "host": host,
        "key": api_key,
        "keyLocation": key_location,
        "urlList": urls,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    success = response.status_code in [200, 202]
    logger.info(f"IndexNow [{engine}] response: {response.status_code} for {len(urls)} URLs")

    return {
        "status_code": response.status_code,
        "success": success,
        "engine": engine,
    }
