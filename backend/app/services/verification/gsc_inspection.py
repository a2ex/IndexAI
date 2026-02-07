import logging
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


def check_indexed_gsc_inspection(
    url: str, site_url: str, service_account_json: str
) -> dict:
    """
    Check indexation status via GSC URL Inspection API.
    Quota: 2000 requests/day/property, 600/minute.
    """
    SCOPES = ["https://www.googleapis.com/auth/webmasters"]

    credentials = service_account.Credentials.from_service_account_file(
        service_account_json, scopes=SCOPES
    )
    credentials.refresh(Request())

    api_url = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
    headers = {"Authorization": f"Bearer {credentials.token}"}
    payload = {"inspectionUrl": url, "siteUrl": site_url}

    response = requests.post(api_url, json=payload, headers=headers)
    data = response.json()

    if response.status_code == 200:
        inspection = data.get("inspectionResult", {})
        index_status = inspection.get("indexStatusResult", {})

        verdict = index_status.get("verdict", "UNKNOWN")
        coverage_state = index_status.get("coverageState", "")
        is_indexed = verdict == "PASS"

        return {
            "is_indexed": is_indexed,
            "verdict": verdict,
            "coverage_state": coverage_state,
            "last_crawl_time": index_status.get("lastCrawlTime"),
            "crawled_as": index_status.get("crawledAs"),
            "google_canonical": index_status.get("googleCanonical"),
            "user_canonical": index_status.get("userCanonical"),
            "robots_txt_state": index_status.get("robotsTxtState"),
            "indexing_state": index_status.get("indexingState"),
            "method": "gsc_inspection",
        }
    else:
        logger.error(f"GSC Inspection failed for {url}: {data}")
        return {
            "is_indexed": None,
            "error": data,
            "method": "gsc_inspection",
        }
