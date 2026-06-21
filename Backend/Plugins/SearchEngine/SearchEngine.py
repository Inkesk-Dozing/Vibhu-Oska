"""
Vibhu-Oska AI-OS — SearchEngine Plugin
Self-hosted SearXNG integration for zero-API deep web research.
Implements DeepResearch mode: multi-page scraping + AI summarization.
"""

from __future__ import annotations

import asyncio
import html
import re
import urllib.parse
from typing import Any

import httpx

from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Backend.Plugins.Logger.Logger import Logger
from Backend.Plugins.ConfigLoader.ConfigLoader import ConfigLoader
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class SearchResult:
    """Single search result from SearXNG."""
    __slots__ = ("title", "url", "snippet", "content", "score")

    def __init__(self, title: str, url: str, snippet: str = "", content: str = "", score: float = 0.0) -> None:
        self.title   = title
        self.url     = url
        self.snippet = snippet
        self.content = content
        self.score   = score

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet, "content": self.content, "score": self.score}


class SearchEngine(BaseService):
    """
    SearXNG-backed search plugin for Vibhu-Oska.
    Wraps the local SearXNG Docker container and provides:
      - Standard search: top-N results
      - DeepResearch: fetch + extract + synthesize full page content
    """

    def __init__(self) -> None:
        self._searxng_url = "http://localhost:8080"
        self._timeout     = 15.0
        self._initialized = False
        self._log         = Logger.get("SearchEngine")

    # ══════════════════════════════════════════════════════════════
    # BaseService Interface
    # ══════════════════════════════════════════════════════════════

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="search_engine",
            version="0.1.0",
            description="Self-hosted SearXNG web research engine",
            capabilities=["search", "deep_research", "scrape"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self._initialized:
            return
        config = ConfigLoader.load()
        self._searxng_url = config.get("plugins.search.searxng_url", "http://localhost:8080")
        self._timeout     = float(config.get("plugins.search.timeout", 15.0))

        # Verify SearXNG is reachable
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._searxng_url}/healthz")
                if resp.status_code < 500:
                    self._initialized = True
                    self._log.info("SearchEngine connected to SearXNG", url=self._searxng_url)
                else:
                    self._log.warning("SearXNG health check returned non-OK status", status=resp.status_code)
                    self._initialized = True  # Still mark initialized — may work for search
        except Exception as e:
            self._log.warning("SearXNG unreachable (will retry on first use)", error=str(e))
            self._initialized = True  # Mark initialized so the plugin is registered

    async def shutdown(self) -> None:
        self._initialized = False

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "search":
            return await self.search(
                query=kwargs["query"],
                num_results=int(kwargs.get("num_results", 5)),
                categories=kwargs.get("categories", "general"),
            )
        elif action == "deep_research":
            return await self.deep_research(
                query=kwargs["query"],
                num_sources=int(kwargs.get("num_sources", 3)),
            )
        elif action == "scrape":
            return await self.scrape_url(kwargs["url"])
        else:
            raise ValueError(f"Unknown SearchEngine action: {action}")

    # ══════════════════════════════════════════════════════════════
    # Search
    # ══════════════════════════════════════════════════════════════

    async def search(
        self,
        query: str,
        num_results: int = 5,
        categories: str = "general",
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """Query SearXNG and return structured results."""
        params = urllib.parse.urlencode({
            "q":         query,
            "format":    "json",
            "categories": categories,
            "language":  language,
            "pageno":    1,
        })
        url = f"{self._searxng_url}/search?{params}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, headers={"Accept": "application/json"})
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError:
            self._log.error("SearXNG not reachable — ensure Docker container is running")
            return [{"title": "SearXNG Offline", "url": "", "snippet": "Start SearXNG with: docker-compose up searxng", "content": "", "score": 0.0}]
        except Exception as e:
            self._log.error("SearXNG search error", error=str(e))
            raise RuntimeError(f"SearchEngine query failed: {e}") from e

        results = []
        for r in data.get("results", [])[:num_results]:
            results.append(SearchResult(
                title   = r.get("title", ""),
                url     = r.get("url", ""),
                snippet = self._clean_html(r.get("content", "")),
                score   = float(r.get("score", 0.0)),
            ).to_dict())

        self._log.info("Search completed", query=query, results=len(results))
        return results

    # ══════════════════════════════════════════════════════════════
    # Deep Research (Multi-Page)
    # ══════════════════════════════════════════════════════════════

    async def deep_research(
        self,
        query: str,
        num_sources: int = 3,
    ) -> dict[str, Any]:
        """
        Multi-step deep research:
        1. Search SearXNG for top N URLs
        2. Fetch and extract text from each URL
        3. Return combined corpus for AI synthesis
        """
        self._log.info("Starting deep research", query=query, sources=num_sources)

        # Step 1: Get URLs
        results = await self.search(query, num_results=num_sources + 2)
        urls = [r["url"] for r in results if r["url"]][:num_sources]

        # Step 2: Scrape concurrently
        tasks = [self.scrape_url(url) for url in urls]
        scraped = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 3: Build corpus
        sources = []
        for i, (url, content) in enumerate(zip(urls, scraped)):
            if isinstance(content, Exception) or not content:
                continue
            sources.append({
                "index":   i + 1,
                "url":     url,
                "title":   results[i].get("title", ""),
                "snippet": results[i].get("snippet", ""),
                "content": content[:3000],  # Cap per source
            })

        return {
            "query":   query,
            "sources": sources,
            "corpus":  "\n\n".join(f"[Source {s['index']}] {s['title']}\nURL: {s['url']}\n{s['content']}" for s in sources),
        }

    # ══════════════════════════════════════════════════════════════
    # URL Scraper
    # ══════════════════════════════════════════════════════════════

    async def scrape_url(self, url: str) -> str:
        """Fetch a URL and extract readable text content."""
        if not url or not url.startswith("http"):
            return ""
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": "Vibhu-Oska-Research/0.1 (+local-agent)"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                raw = resp.text
        except Exception as e:
            self._log.debug("Scrape failed", url=url, error=str(e))
            return ""

        return self._extract_text(raw)

    # ══════════════════════════════════════════════════════════════
    # Text Extraction
    # ══════════════════════════════════════════════════════════════

    def _extract_text(self, html_content: str) -> str:
        """Extract readable text from HTML by stripping tags and normalizing."""
        # Remove script and style blocks entirely
        text = re.sub(r'<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Decode HTML entities
        text = html.unescape(text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove very short lines (menu items, buttons)
        lines = [line.strip() for line in text.split('. ') if len(line.strip()) > 40]
        return '. '.join(lines[:100])  # Cap at ~100 sentences

    def _clean_html(self, text: str) -> str:
        """Quick HTML strip for snippets."""
        text = re.sub(r'<[^>]+>', '', text)
        return html.unescape(text).strip()
