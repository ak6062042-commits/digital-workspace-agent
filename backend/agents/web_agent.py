"""Live web research with source-attributed local synthesis."""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

from backend.core.config import settings
from backend.core.text_analysis import key_takeaways, summarize_text
from backend.tools.browser_tool import search_in_browser
from backend.tools.fetch_tool import fetch_webpage_content
from backend.tools.search_tool import search_web


logger = logging.getLogger("WebResearchAgent")


class WebResearchAgent:
    """Search, read a useful subset of sources, and return a concise cited brief."""

    @staticmethod
    def _clean_search_query(query: str) -> str:
        cleaned = re.sub(
            r"(?i)\b(search it on the browser|search on the browser|search on browser|search in the browser|search in browser|search this on the browser|on the browser|in the browser|on browser|in browser|open browser and search|open browser for|open browser to|browse to|open tab for)\b",
            "",
            query,
        ).strip()
        cleaned = re.sub(r"(?i)^(search for|search|find|look up|research|compare)\s+", "", cleaned).strip(" :.-")
        return cleaned if len(cleaned) > 2 else query.strip()

    @staticmethod
    def _browser_engine() -> str:
        provider = settings.web_search_provider
        return provider if provider in {"google", "duckduckgo", "bing"} else "duckduckgo"

    @staticmethod
    def _source_record(result: dict[str, str], content: str | None = None) -> dict[str, str]:
        url = result.get("url", "")
        return {
            "title": result.get("title") or urlparse(url).netloc or "Untitled source",
            "url": url,
            "domain": result.get("domain") or urlparse(url).netloc.removeprefix("www."),
            "snippet": result.get("snippet", ""),
            "summary": summarize_text(content or result.get("snippet", ""), maximum_sentences=2, maximum_characters=500),
        }

    @staticmethod
    def _markdown_link(title: str, url: str) -> str:
        safe_title = (title or url).replace("[", "\\[").replace("]", "\\]")
        safe_url = url.replace("(", "%28").replace(")", "%29")
        return f"[{safe_title}]({safe_url})"

    def _build_brief(self, query: str, sources: list[dict[str, str]], browser_info: dict[str, Any] | None) -> str:
        lines = [f"## Research brief: {query}"]
        if browser_info and browser_info.get("success"):
            lines.append(f"I also opened a live {browser_info.get('engine', 'web')} search in your browser.")
        lines.append(f"I found {len(sources)} source{'s' if len(sources) != 1 else ''} and read the leading result pages where they were available.")
        lines.extend(["", "### Key findings"])
        for source in sources:
            link = self._markdown_link(source["title"], source["url"])
            summary = source.get("summary") or source.get("snippet") or "The source did not provide a readable extract."
            lines.append(f"- **{link}** ({source.get('domain') or 'web'}): {summary}")
        lines.extend(["", "### Sources"])
        for index, source in enumerate(sources, 1):
            lines.append(f"{index}. {self._markdown_link(source['title'], source['url'])} — {source.get('domain') or 'web'}")
        return "\n".join(lines)

    def handle(self, query: str, launch_browser: bool = False) -> dict[str, Any]:
        clean_query = self._clean_search_query(query)
        if not clean_query:
            return {"agent": "web_agent", "response": "Tell me what you want researched.", "search_results": [], "sources": [], "browser_info": None, "tasks_created": []}

        browser_info = None
        if launch_browser:
            try:
                browser_info = search_in_browser(clean_query, engine=self._browser_engine(), bring_to_front=True)
            except Exception as error:
                logger.info("Could not launch browser research: %s", error)

        if settings.web_search_provider in {"chrome", "browser", "manual"}:
            response = (
                f"Opened a browser search for **{clean_query}**. Browser-only mode is active, so I did not retrieve pages into the assistant."
                if browser_info and browser_info.get("success")
                else f"Browser-only mode is active. Prepared a browser search for **{clean_query}**, but the browser could not be launched."
            )
            return {"agent": "web_agent", "response": response, "search_results": [], "sources": [], "browser_info": browser_info, "tasks_created": []}

        results = search_web(clean_query, max_results=settings.research_max_results)
        sources: list[dict[str, str]] = []
        for index, result in enumerate(results):
            content = None
            if index < settings.research_fetch_results:
                content = fetch_webpage_content(result.get("url", ""), max_chars=settings.research_max_chars)
                if content.startswith(("Error:", "Failed to fetch", "Failed to extract")):
                    content = None
            sources.append(self._source_record(result, content))

        return {
            "agent": "web_agent",
            "response": self._build_brief(clean_query, sources, browser_info),
            "search_results": results,
            "sources": sources,
            "browser_info": browser_info,
            "tasks_created": [],
        }

    @staticmethod
    def related_document_queries(title: str) -> list[dict[str, str]]:
        subject = re.sub(r"\s+[-|–—].*$", "", (title or "")).strip()[:160]
        if not subject:
            return []
        topics = [f"{subject} documentation", f"{subject} examples", f"{subject} best practices"]
        return [{"label": topic, "query": topic} for topic in topics]
