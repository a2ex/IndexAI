import logging
from urllib.parse import urlparse

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/webmasters"]

# Caches
_sites_cache: dict[str, list[str]] = {}
_creds_cache: dict[str, service_account.Credentials] = {}


def _get_credentials(service_account_info: dict):
    cache_key = service_account_info.get("client_email", "")
    if cache_key in _creds_cache:
        creds = _creds_cache[cache_key]
        if creds.valid:
            return creds
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    creds.refresh(Request())
    _creds_cache[cache_key] = creds
    return creds


def _list_gsc_sites(service_account_info: dict) -> list[str]:
    """List all GSC site URLs accessible by the service account (cached)."""
    cache_key = service_account_info.get("client_email", "")
    if cache_key in _sites_cache:
        return _sites_cache[cache_key]

    credentials = _get_credentials(service_account_info)
    resp = requests.get(
        "https://www.googleapis.com/webmasters/v3/sites",
        headers={"Authorization": f"Bearer {credentials.token}"},
        timeout=15,
    )
    if resp.status_code == 200:
        sites = [s["siteUrl"] for s in resp.json().get("siteEntry", [])]
        _sites_cache[cache_key] = sites
        return sites
    return []


def _match_gsc_property(url: str, service_account_info: dict, default_site_url: str) -> str:
    """Find the GSC property that matches the URL's domain."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    sites = _list_gsc_sites(service_account_info)
    for site in sites:
        site_host = urlparse(site).hostname or ""
        # Match: URL host equals or is subdomain of site host
        if hostname == site_host or hostname.endswith("." + site_host):
            return site

    return default_site_url


def check_indexed_gsc_inspection(
    url: str, site_url: str, service_account_info: dict
) -> dict:
    """
    Check indexation status via GSC URL Inspection API.
    Automatically selects the right GSC property for the URL's domain.
    Quota: 2000 requests/day/property, 600/minute.
    """
    matched_property = _match_gsc_property(url, service_account_info, site_url)
    credentials = _get_credentials(service_account_info)

    api_url = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
    headers = {"Authorization": f"Bearer {credentials.token}"}
    payload = {"inspectionUrl": url, "siteUrl": matched_property}

    response = requests.post(api_url, json=payload, headers=headers, timeout=30)
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
        logger.error(f"GSC Inspection failed for {url} (property={matched_property}): {data}")
        return {
            "is_indexed": None,
            "error": data,
            "method": "gsc_inspection",
        }
