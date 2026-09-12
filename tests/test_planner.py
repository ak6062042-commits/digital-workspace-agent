import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.orchestration.planner import Planner
from backend.agents.web_agent import WebResearchAgent
from backend.coordinator.scheduler import PlannerScheduler
from backend.db.models import Task
from backend.main import _writing_research_topics, _writing_suggestion
from backend.agents.state_agent import DigitalStateAgent


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = Planner()

    def test_workspace_question_only_observes(self):
        plan = self.planner.plan("What changed while I was away?")
        self.assertEqual(plan.action, "state.diff")
        self.assertEqual(plan.category, "observe")

    def test_allowlisted_application_is_a_controlled_action(self):
        plan = self.planner.plan("Open VS Code")
        self.assertEqual(plan.action, "desktop.open_app")
        self.assertEqual(plan.arguments["app_id"], "vscode")

    def test_unknown_application_is_not_executed(self):
        plan = self.planner.plan("Open powershell & whoami")
        self.assertNotEqual(plan.action, "desktop.open_app")

    def test_research_is_a_hybrid_plan(self):
        plan = self.planner.plan("Research PPO reward shaping")
        self.assertEqual(plan.action, "web.research")
        self.assertEqual(plan.category, "hybrid")
        self.assertTrue(plan.arguments["launch_browser"])

    def test_open_this_tab_uses_only_the_reported_http_url(self):
        plan = self.planner.plan("Open this tab", {"browser_url": "https://example.com/guide"})
        self.assertEqual(plan.action, "browser.open_url")
        self.assertEqual(plan.arguments["url"], "https://example.com/guide")

    def test_open_this_tab_explains_how_to_enable_tab_context(self):
        plan = self.planner.plan("Open this tab", {"browser_url": None})
        self.assertEqual(plan.action, "conversation.respond")
        self.assertIn("Active-tab metadata sync", plan.arguments["response"])

    def test_word_is_an_approved_writing_application(self):
        plan = self.planner.plan("Open Microsoft Word")
        self.assertEqual(plan.action, "desktop.open_app")
        self.assertEqual(plan.arguments["app_id"], "word")

    def test_current_topic_research_uses_workspace_context(self):
        plan = self.planner.plan("Research this current topic", {"browser_tab_title": "FastAPI deployment guide"})
        self.assertEqual(plan.action, "web.research")
        self.assertEqual(plan.arguments["query"], "FastAPI deployment guide")

    def test_related_document_topics_are_text_queries_not_urls(self):
        topics = WebResearchAgent.related_document_queries("FastAPI deployment guide - Google Docs")
        self.assertEqual(len(topics), 3)
        self.assertTrue(all(topic["query"].startswith("FastAPI deployment guide") for topic in topics))
        self.assertTrue(all("url" not in topic for topic in topics))

    @patch("backend.agents.web_agent.search_web")
    @patch("backend.agents.web_agent.search_in_browser", return_value={"success": True})
    def test_chrome_research_does_not_fetch_or_summarize_web_results(self, browser_search, web_search):
        result = WebResearchAgent().handle("FastAPI deployment", launch_browser=True)
        self.assertEqual(result["search_results"], [])
        self.assertIn("No web pages were fetched", result["response"])
        browser_search.assert_called_once()
        web_search.assert_not_called()

    def test_unrelated_browser_url_does_not_trigger_document_suggestions(self):
        scheduler = PlannerScheduler(None)
        snapshot = SimpleNamespace(active_app="chrome.exe", active_window_title="Example", browser_tab_title="Example", browser_url="https://example.com/products")
        self.assertFalse(scheduler._looks_like_document_context(snapshot))

    def test_writing_improvement_includes_a_local_rewrite_and_text_keywords(self):
        text = "In order to improve FastAPI authentication, we should use OAuth2 examples."
        improvement = _writing_suggestion(text, "improve")
        topics = _writing_research_topics(text, "Microsoft Word selection")
        self.assertIn("Suggested local rewrite", improvement)
        self.assertIn("fastapi", topics["keywords"])
        self.assertTrue(all("url" not in topic for topic in topics["related_queries"]))

    def test_python_widget_context_is_not_reopenable_task_context(self):
        self.assertFalse(Task(source_app="python.exe").to_dict()["has_context"])
        self.assertTrue(Task(source_app="Code.exe").to_dict()["has_context"])

    def test_agent_dashboard_is_not_saved_as_task_context(self):
        dashboard = SimpleNamespace(browser_url="http://localhost:5173", active_app="Google Chrome", active_window_title="Digital Workspace Agent")
        real_local_app = SimpleNamespace(browser_url="http://localhost:3000/projects", active_app="Google Chrome", active_window_title="Project")
        self.assertTrue(DigitalStateAgent._is_agent_control_surface(dashboard))
        self.assertFalse(DigitalStateAgent._is_agent_control_surface(real_local_app))
        self.assertFalse(Task(source_url=dashboard.browser_url, source_app=dashboard.active_app).to_dict()["has_context"])


if __name__ == "__main__":
    unittest.main()
