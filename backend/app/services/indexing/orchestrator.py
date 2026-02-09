import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse
from app.config import settings
from app.services.indexing.google_indexing_api import submit_url_google_api, submit_batch_google_api
from app.services.indexing.indexnow import submit_indexnow
from app.services.indexing.social_signals import ping_web_services
from app.services.indexing.backlink_pings import ping_backlink_trackers
from app.services.service_account_manager import ServiceAccountManager

logger = logging.getLogger(__name__)


class IndexingOrchestrator:
    """
    Orchestrates the execution of all 5 indexing methods for each URL.
    Key principle: Google needs to detect a URL from MULTIPLE sources.
    """

    def __init__(self, sa_manager: ServiceAccountManager):
        self.sa_manager = sa_manager

    async def submit_url(
        self,
        url: str,
        indexnow_config: Optional[dict] = None,
        sitemap_url: Optional[str] = None,
    ) -> dict:
        """Submit a URL via all available methods in parallel."""
        results = {}
        tasks = []

        # Method 1: Google Indexing API (with service account rotation)
        sa = await self.sa_manager.get_next_available()
        if sa:
            tasks.append(self._run_method(
                "google_api",
                lambda: submit_url_google_api(url, sa.json_key_path),
            ))

        # Method 2: IndexNow (project config or global fallback)
        inow_config = indexnow_config
        if not inow_config and settings.INDEXNOW_API_KEY:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            inow_config = {
                "host": host,
                "api_key": settings.INDEXNOW_API_KEY,
                "key_location": f"https://{host}/{settings.INDEXNOW_API_KEY}.txt",
            }
        if inow_config:
            tasks.append(self._run_method(
                "indexnow",
                lambda: submit_indexnow(
                    [url],
                    inow_config["host"],
                    inow_config["api_key"],
                    inow_config["key_location"],
                ),
            ))

        # Method 3: Social signals / Web pings
        tasks.append(self._run_method(
            "social_signals",
            lambda: ping_web_services(url),
        ))

        # Method 4: Backlink pings
        tasks.append(self._run_method(
            "backlink_pings",
            lambda: ping_backlink_trackers(url),
        ))

        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, tuple):
                name, result = item
                results[name] = result
            else:
                logger.error(f"Unexpected error in orchestrator: {item}")

        # Update service account usage
        if sa:
            await self.sa_manager.increment_usage(sa.id, 1)

        return results

    async def _run_method(self, name: str, func) -> tuple:
        """Execute a method with error handling."""
        try:
            result = func()
            if asyncio.iscoroutine(result):
                result = await result
            return (name, {"success": True, "data": result})
        except Exception as e:
            logger.error(f"Method {name} failed: {e}")
            return (name, {"success": False, "error": str(e)})

    async def submit_batch(
        self,
        urls: list[str],
        indexnow_config: Optional[dict] = None,
        sitemap_url: Optional[str] = None,
    ) -> dict:
        """Submit a batch of URLs using all methods."""
        results = {"google_api": [], "indexnow": None, "individual": []}

        # Google API in batches of 100
        sa = await self.sa_manager.get_next_available()
        if sa:
            for i in range(0, len(urls), 100):
                chunk = urls[i : i + 100]
                batch_result = submit_batch_google_api(chunk, sa.json_key_path)
                results["google_api"].extend(batch_result)
                await self.sa_manager.increment_usage(sa.id, len(chunk))

        # IndexNow in a single request (project config or global fallback)
        inow_config = indexnow_config
        if not inow_config and settings.INDEXNOW_API_KEY and urls:
            parsed = urlparse(urls[0])
            host = parsed.hostname or ""
            inow_config = {
                "host": host,
                "api_key": settings.INDEXNOW_API_KEY,
                "key_location": f"https://{host}/{settings.INDEXNOW_API_KEY}.txt",
            }
        if inow_config:
            results["indexnow"] = await submit_indexnow(
                urls,
                inow_config["host"],
                inow_config["api_key"],
                inow_config["key_location"],
            )

        # Individual pings (limit parallelism)
        semaphore = asyncio.Semaphore(10)

        async def ping_url(url):
            async with semaphore:
                social = await ping_web_services(url)
                backlink = await ping_backlink_trackers(url)
                return {"url": url, "social": social, "backlink": backlink}

        individual_tasks = [ping_url(url) for url in urls]
        results["individual"] = await asyncio.gather(*individual_tasks, return_exceptions=True)

        return results
