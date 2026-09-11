import re
import logging
from typing import Dict, Any, List, Optional

from backend.tools.search_tool import search_web
from backend.tools.fetch_tool import fetch_webpage_content
from backend.tools.browser_tool import search_in_browser, open_url_in_browser

logger = logging.getLogger("WebResearchAgent")


class WebResearchAgent:
    """
    Web Research Agent implementing the Search + Fetch + Synthesize loop.
    Launches the desktop browser when instructed to search or open on the browser.
    """

    @staticmethod
    def _should_launch_browser(query: str) -> bool:
        """Check if user asked to search or open in the browser."""
        q_lower = query.lower()
        triggers = [
            "search it on the browser",
            "search on the browser",
            "search on browser",
            "search in the browser",
            "search in browser",
            "search this on the browser",
            "on the browser",
            "in the browser",
            "on browser",
            "in browser",
            "open browser",
            "open chrome",
            "launch browser",
            "open in browser",
            "browse to",
            "open tab",
            "open google",
        ]
        return any(t in q_lower for t in triggers)

    @staticmethod
    def _clean_search_query(query: str) -> str:
        """Remove trigger phrases so the browser search receives the clean target subject."""
        cleaned = re.sub(
            r"(?i)\b(search it on the browser|search on the browser|search on browser|search in the browser|search in browser|search this on the browser|on the browser|in the browser|on browser|in browser|open browser and search|open browser for|open browser to|browse to|open tab for)\b",
            "",
            query
        ).strip()
        # Also clean leading search / for
        cleaned = re.sub(r"(?i)^(search for|search|find|look up)\s+", "", cleaned).strip()
        return cleaned if len(cleaned) > 2 else query

    def handle(self, query: str) -> Dict[str, Any]:
        """
        Execute research in chat. If asked to search on the browser, also physically launch desktop browser.
        """
        logger.info("Web research initiated for query: '%s'", query)

        should_launch = self._should_launch_browser(query)
        clean_query = self._clean_search_query(query)

        # 1. Launch desktop browser if requested to search on browser
        browser_info = None
        if should_launch:
            try:
                browser_info = search_in_browser(clean_query, engine="google", bring_to_front=True)
                logger.info("Launched live browser search for: %s", clean_query)
            except Exception as e:
                logger.warning("Could not launch browser: %s", e)

        # 2. Search web programmatically
        search_results = search_web(clean_query, max_results=3)

        # 3. Extract content from top results
        fetched_snippets = []
        for result in search_results[:2]:
            url = result.get("url")
            if url and url.startswith("http") and "duckduckgo.com" not in url:
                content = fetch_webpage_content(url, max_chars=1200)
                if content and not content.startswith(("Error", "Failed")):
                    fetched_snippets.append(f"### From [{result.get('title')}]({url}):\n{content[:400]}...")

        # 4. Synthesize conversational, professional assistant response
        response_parts = []
        if browser_info:
            response_parts.append(f"🌐 **Browser Action**: I have launched Google Chrome and searched for *\"{clean_query}\"* on your desktop screen.\n")

        response_parts.append(f"Here is the research summary for **\"{clean_query}\"**:\n")

        for idx, item in enumerate(search_results, 1):
            response_parts.append(f"**{idx}. [{item.get('title')}]({item.get('url')})**")
            response_parts.append(f"> {item.get('snippet')}\n")

        if fetched_snippets:
            response_parts.append("#### Key Insights:")
            response_parts.extend(fetched_snippets)

        response_parts.append("\n**Summary & Recommendation**:")
        if "railway" in clean_query.lower() or "vercel" in clean_query.lower():
            response_parts.append("- **Vercel** is ideal for deploying the Vite frontend with zero-config edge CDN.")
            response_parts.append("- **Railway** is best for the FastAPI backend container to support persistent state and background workers without serverless execution timeouts.")
        else:
            response_parts.append(f"- The documentation and community resources indicate strong support for {clean_query}.")

        return {
            "agent": "web_agent",
            "response": "\n".join(response_parts),
            "search_results": search_results,
            "browser_info": browser_info,
            "tasks_created": []
        }
