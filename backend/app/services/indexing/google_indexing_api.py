import json
import logging
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import httplib2

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/indexing"]
ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"


def submit_url_google_api(url: str, json_key_dict: dict) -> dict:
    """Submit a single URL via Google Indexing API."""
    try:
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            json_key_dict, scopes=SCOPES
        )
        http = credentials.authorize(httplib2.Http())

        body = json.dumps({"url": url, "type": "URL_UPDATED"})
        response, content = http.request(ENDPOINT, method="POST", body=body)
        result = json.loads(content.decode())

        status_code = int(response["status"])
        logger.info(f"Google Indexing API response for {url}: {status_code}")

        return {
            "status_code": status_code,
            "response": result,
            "success": status_code == 200,
        }
    except Exception as e:
        logger.error(f"Google Indexing API error for {url}: {e}")
        return {
            "status_code": 0,
            "response": {"error": str(e)},
            "success": False,
        }


def submit_batch_google_api(urls: list[str], json_key_dict: dict) -> list[dict]:
    """Submit a batch of URLs (max 100) via Google Indexing API."""
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        json_key_dict, scopes=SCOPES
    )
    service = build("indexing", "v3", credentials=credentials)

    results = []

    def callback(request_id, response, exception):
        if exception:
            results.append({"url": request_id, "error": str(exception), "success": False})
        else:
            results.append({"url": request_id, "response": response, "success": True})

    batch = service.new_batch_http_request(callback=callback)

    for url in urls[:100]:
        batch.add(
            service.urlNotifications().publish(
                body={"url": url, "type": "URL_UPDATED"}
            ),
            request_id=url,
        )

    batch.execute()
    logger.info(f"Google Indexing API batch submitted {len(urls)} URLs")
    return results
