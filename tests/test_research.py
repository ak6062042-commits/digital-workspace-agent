import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.agents.web_agent import WebResearchAgent
from backend.core.text_analysis import extract_keywords, summarize_text
from backend.main import BrowserSummarizeRequest, summarize_browser_tab
from backend.tools.fetch_tool import fetch_webpage_content, is_safe_research_url
from backend.tools.search_tool import search_exa, search_web


class ResearchTests(unittest.TestCase):
    def test_html_search_results_are_parsed_and_unwrapped(self):
        html = """
        <div class="result results_links">
          <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fguide">Example Guide</a>
          <a class="result__snippet">Useful current material from the source.</a>
        </div>
        """
        response = SimpleNamespace(text=html, raise_for_status=lambda: None)
        with patch("backend.tools.search_tool.requests.get", return_value=response):
            results = search_web("example topic", max_results=3)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://example.com/guide")
        self.assertEqual(results[0]["domain"], "example.com")
        self.assertIn("Useful current material", results[0]["snippet"])

    def test_exa_search_uses_inline_source_text(self):
        response = SimpleNamespace(
            json=lambda: {
                "results": [
                    {
                        "title": "Exa result",
                        "url": "https://example.com/guide",
                        "text": "Useful extracted source text for the research brief.",
                    }
                ]
            },
            raise_for_status=lambda: None,
        )
        with patch("backend.tools.search_tool.requests.post", return_value=response) as request_post:
            results = search_exa("example topic", api_key="test-key", max_results=3, max_characters=1000)
        self.assertEqual(results[0]["provider"], "exa")
        self.assertEqual(results[0]["content"], "Useful extracted source text for the research brief.")
        self.assertEqual(request_post.call_args.kwargs["headers"]["x-api-key"], "test-key")
        self.assertEqual(request_post.call_args.kwargs["json"]["contents"]["text"]["maxCharacters"], 1000)

    @patch("backend.agents.web_agent.search_in_browser", return_value={"success": True, "engine": "duckduckgo", "search_url": "https://duckduckgo.com/?q=topic"})
    @patch("backend.agents.web_agent.fetch_webpage_content", return_value="FastAPI deploys applications. Deployment guidance recommends a repeatable release process. Teams should monitor releases and roll back failed changes.")
    @patch("backend.agents.web_agent.search_web", return_value=[
        {"title": "Official deployment guide", "url": "https://fastapi.tiangolo.com/deployment/", "domain": "fastapi.tiangolo.com", "snippet": "Deployment documentation."},
        {"title": "Operational guide", "url": "https://example.com/operations", "domain": "example.com", "snippet": "Operational notes."},
    ])
    @patch("backend.agents.web_agent.settings", SimpleNamespace(web_search_provider="duckduckgo", research_max_results=6, research_fetch_results=2, research_max_chars=6000))
    def test_live_research_fetches_sources_and_returns_attributed_brief(self, _search, fetch, browser):
        result = WebResearchAgent().handle("Research FastAPI deployment", launch_browser=True)
        self.assertEqual(len(result["sources"]), 2)
        self.assertEqual(fetch.call_count, 2)
        self.assertTrue(browser.called)
        self.assertIn("## Research brief: FastAPI deployment", result["response"])
        self.assertIn("Official deployment guide", result["response"])

    @patch("backend.agents.web_agent.fetch_webpage_content")
    @patch("backend.agents.web_agent.search_web")
    @patch("backend.agents.web_agent.search_exa", return_value=[
        {
            "title": "Exa source",
            "url": "https://example.com/exa",
            "domain": "example.com",
            "snippet": "Inline Exa content.",
            "content": "Inline Exa content with enough detail to summarize.",
            "provider": "exa",
        }
    ])
    @patch("backend.agents.web_agent.settings", SimpleNamespace(web_search_provider="exa", exa_api_key="test-key", research_max_results=6, research_fetch_results=2, research_max_chars=6000))
    def test_exa_is_preferred_and_inline_text_avoids_duplicate_fetch(self, exa, fallback, fetch):
        result = WebResearchAgent().handle("Research Exa integration")
        self.assertEqual(result["research_provider"], "Exa")
        self.assertIn("Research provider: **Exa**", result["response"])
        exa.assert_called_once()
        fallback.assert_not_called()
        fetch.assert_not_called()

    @patch("backend.agents.web_agent.search_web", return_value=[
        {"title": "Fallback source", "url": "https://example.com/fallback", "domain": "example.com", "snippet": "Fallback content."}
    ])
    @patch("backend.agents.web_agent.search_exa", return_value=[])
    @patch("backend.agents.web_agent.settings", SimpleNamespace(web_search_provider="exa", exa_api_key="missing-or-invalid", research_max_results=6, research_fetch_results=0, research_max_chars=6000))
    def test_duckduckgo_is_used_when_exa_returns_no_results(self, exa, fallback):
        result = WebResearchAgent().handle("Research fallback behavior")
        self.assertEqual(result["research_provider"], "DuckDuckGo fallback")
        exa.assert_called_once()
        fallback.assert_called_once()

    @patch("backend.agents.web_agent.search_web")
    @patch("backend.agents.web_agent.settings", SimpleNamespace(web_search_provider="chrome", research_max_results=6, research_fetch_results=4, research_max_chars=6000))
    def test_browser_only_mode_does_not_fetch_pages(self, search):
        result = WebResearchAgent().handle("Research FastAPI deployment")
        self.assertEqual(result["sources"], [])
        self.assertIn("Browser-only mode", result["response"])
        search.assert_not_called()

    def test_extractive_summary_selects_relevant_sentences_and_keywords(self):
        text = (
            "FastAPI makes it straightforward to build typed APIs. "
            "FastAPI deployment needs a reliable process and monitoring. "
            "A reliable deployment process helps teams roll back quickly. "
            "Tea is often served warm in the afternoon."
        )
        summary = summarize_text(text, maximum_sentences=2)
        keywords = extract_keywords(text, maximum=4)
        self.assertIn("deployment", summary.lower())
        self.assertIn("fastapi", keywords)

    def test_browser_summary_accepts_useful_page_length_and_returns_metadata(self):
        content = "FastAPI deployment benefits from repeatable releases and active monitoring. " * 160
        result = summarize_browser_tab(BrowserSummarizeRequest(url="https://example.com/guide", title="Guide", content=content, consent=True))
        self.assertTrue(result["success"])
        self.assertGreater(result["word_count"], 500)
        self.assertIn("fastapi", result["keywords"])
        self.assertTrue(result["key_takeaways"])

    def test_automated_research_rejects_local_or_credential_bearing_urls(self):
        self.assertFalse(is_safe_research_url("http://127.0.0.1:8000/private"))
        self.assertFalse(is_safe_research_url("http://user:pass@example.com/"))
        self.assertFalse(is_safe_research_url("https://workspace.local/internal"))

    @patch("backend.tools.fetch_tool.requests.get")
    @patch("backend.tools.fetch_tool.is_safe_research_url", side_effect=[True, True, False])
    def test_redirect_to_non_public_target_is_not_retrieved(self, safe_url, request_get):
        redirect = Mock(is_redirect=True, headers={"location": "http://127.0.0.1:8000/private"})
        request_get.return_value = redirect
        result = fetch_webpage_content("https://example.com/article")
        self.assertIn("non-public destination", result)
        redirect.close.assert_called_once()
        request_get.assert_called_once()
        self.assertEqual(safe_url.call_count, 3)


if __name__ == "__main__":
    unittest.main()
