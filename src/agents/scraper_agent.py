"""
Scraper Agent — Web scraping with requests/BeautifulSoup.

Ingests web content → Events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScraperTask:
    url: str
    selector: str | None = None
    tenant_id: str = "system"
    space_id: str = "system"
    user_id: str = "system"


class ScraperAgent:
    """Web scraper agent."""

    async def run(self, task: ScraperTask) -> dict[str, Any]:
        """Scrape URL and return content."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(task.url)
                resp.raise_for_status()
                html = resp.text

            texts: list[str] = []
            if task.selector:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")
                    elements = soup.select(task.selector)
                    texts = [el.get_text(strip=True) for el in elements]
                except ImportError:
                    logger.warning("BeautifulSoup not installed; returning raw HTML")
                    texts = [html[:5000]]
            else:
                texts = [html[:10000]]

            return {
                "ok": True,
                "url": task.url,
                "count": len(texts),
                "samples": texts[:5],
                "full_content": "\n\n".join(texts),
            }
        except Exception as e:
            logger.error("ScraperAgent failed: %s", e)
            return {"ok": False, "error": str(e), "url": task.url}
