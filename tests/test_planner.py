import unittest

from backend.orchestration.planner import Planner


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


if __name__ == "__main__":
    unittest.main()
