import logging
import xml.etree.ElementTree as ET

import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# XML namespaces for sitemap parsing
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _get_credentials(service_account_json: str):
    credentials = service_account.Credentials.from_service_account_file(
        service_account_json, scopes=SCOPES
    )
    credentials.refresh(Request())
    return credentials


def list_sitemaps(site_url: str, service_account_json: str) -> list[dict]:
    """
    List sitemaps registered in Google Search Console for the given property.
    Returns list of dicts with path, lastSubmitted, isPending, contents (url count).
    """
    credentials = _get_credentials(service_account_json)
    headers = {"Authorization": f"Bearer {credentials.token}"}

    # site_url must be URL-encoded in the path
    import urllib.parse

    encoded_site = urllib.parse.quote(site_url, safe="")
    api_url = f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/sitemaps"

    response = httpx.get(api_url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    sitemaps = []
    for sm in data.get("sitemap", []):
        urls_count = 0
        for content in sm.get("contents", []):
            if content.get("type") == "web":
                urls_count += int(content.get("submitted", 0))

        sitemaps.append({
            "path": sm.get("path", ""),
            "lastSubmitted": sm.get("lastSubmitted", ""),
            "isPending": sm.get("isPending", False),
            "urls_count": urls_count,
        })

    return sitemaps


SITEMAP_CANDIDATES = [
    "/sitemap_index.xml",   # Yoast SEO
    "/sitemap-index.xml",   # common variant
    "/sitemap.xml",         # generic (often redirects)
    "/wp-sitemap.xml",      # WordPress core
]


async def _count_sitemap_urls(client: httpx.AsyncClient, sitemap_url: str) -> int:
    """Fetch a single sitemap XML and return the number of <url> entries."""
    try:
        resp = await client.get(sitemap_url)
        if resp.status_code != 200:
            return 0
        root = ET.fromstring(resp.content.lstrip())
        return len(root.findall("sm:url", SITEMAP_NS))
    except Exception:
        return 0


async def discover_sitemap_index(domain: str) -> list[dict] | None:
    """
    Probe common sitemap paths on https://<domain> and return sitemap entries
    from the first one that returns valid XML.  Returns None on any failure.
    """
    import asyncio

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for path in SITEMAP_CANDIDATES:
            url = f"https://{domain}{path}"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                root = ET.fromstring(resp.content.lstrip())
                tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

                if tag == "sitemapindex":
                    locs: list[str] = []
                    for sitemap_el in root.findall("sm:sitemap", SITEMAP_NS):
                        loc = sitemap_el.find("sm:loc", SITEMAP_NS)
                        if loc is not None and loc.text:
                            locs.append(loc.text.strip())
                    if not locs:
                        continue
                    # Fetch URL counts concurrently
                    counts = await asyncio.gather(
                        *[_count_sitemap_urls(client, loc) for loc in locs]
                    )
                    sitemaps: list[dict] = []
                    for loc, count in zip(locs, counts):
                        sitemaps.append({
                            "path": loc,
                            "lastSubmitted": "",
                            "isPending": False,
                            "urls_count": count,
                        })
                    return sitemaps

                elif tag == "urlset":
                    # Single sitemap file — return it as the only entry
                    return [{
                        "path": str(resp.url),
                        "lastSubmitted": "",
                        "isPending": False,
                        "urls_count": len(root.findall("sm:url", SITEMAP_NS)),
                    }]

            except Exception as e:
                logger.debug(f"Sitemap probe failed for {url}: {e}")
                continue

    return None


async def fetch_sitemap_urls(sitemap_url: str) -> list[str]:
    """
    Fetch a sitemap XML and extract all <loc> URLs.
    Handles sitemap index files recursively.
    """
    urls: list[str] = []
    visited: set[str] = set()
    await _fetch_sitemap_recursive(sitemap_url, urls, visited)
    return urls


async def _fetch_sitemap_recursive(
    sitemap_url: str, urls: list[str], visited: set[str]
) -> None:
    if sitemap_url in visited:
        return
    visited.add(sitemap_url)

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        response = await client.get(sitemap_url)
        response.raise_for_status()

    root = ET.fromstring(response.content.lstrip())
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    if tag == "sitemapindex":
        # Sitemap index — recurse into each child sitemap
        for sitemap_el in root.findall("sm:sitemap/sm:loc", SITEMAP_NS):
            child_url = sitemap_el.text.strip() if sitemap_el.text else ""
            if child_url:
                await _fetch_sitemap_recursive(child_url, urls, visited)
    else:
        # Regular urlset
        for loc_el in root.findall("sm:url/sm:loc", SITEMAP_NS):
            url = loc_el.text.strip() if loc_el.text else ""
            if url:
                urls.append(url)
