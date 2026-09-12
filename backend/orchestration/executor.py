"""Policy-enforcing executor. This is the only orchestration component that invokes tools."""
from __future__ import annotations

import secrets
from typing import Any

from backend.agents.state_agent import DigitalStateAgent
from backend.agents.task_agent import TaskAgent
from backend.agents.web_agent import WebResearchAgent
from backend.core.config import settings
from backend.orchestration.planner import ExecutionPlan
from backend.tools.browser_tool import open_url_in_browser
from backend.tools.os_tool import open_desktop_app


class Executor:
    def __init__(self) -> None:
        self.state_agent = DigitalStateAgent()
        self.task_agent = TaskAgent()
        self.web_agent = WebResearchAgent()
        self.pending: dict[str, ExecutionPlan] = {}

    def execute_or_propose(self, plan: ExecutionPlan) -> dict[str, Any]:
        if plan.confirmation_required or (plan.category == "consequential"):
            confirmation_id = secrets.token_urlsafe(16)
            self.pending[confirmation_id] = plan
            return {"status": "confirmation_required", "confirmation_id": confirmation_id, "plan": plan.to_dict(), "response": "This action needs your confirmation before it can run."}
        return self.execute(plan)

    def confirm(self, confirmation_id: str, approved: bool) -> dict[str, Any]:
        plan = self.pending.pop(confirmation_id, None)
        if not plan:
            return {"status": "not_found", "response": "That confirmation request is no longer available."}
        if not approved:
            return {"status": "rejected", "plan": plan.to_dict(), "response": "Action cancelled. Nothing was executed."}
        return self.execute(plan)

    def execute(self, plan: ExecutionPlan) -> dict[str, Any]:
        action = plan.action
        if action == "state.latest":
            result = self.state_agent.handle("what was I working on")
        elif action == "state.diff":
            result = self.state_agent.handle("what changed")
        elif action == "task.list":
            result = self.task_agent.handle("show my tasks")
        elif action == "task.create":
            result = self.task_agent.create_task(plan.arguments["title"])
        elif action == "task.complete":
            result = self.task_agent.complete_task(plan.arguments["task_id"])
        elif action == "web.research":
            result = self.web_agent.handle(plan.arguments["query"], launch_browser=bool(plan.arguments.get("launch_browser")))
        elif action == "desktop.open_app":
            launch = open_desktop_app(plan.arguments["app_id"])
            result = {"response": f"Opened {launch.get('app', 'the requested application')}." if launch.get("success") else launch.get("error", "Could not open application."), "browser_info": None, "tasks_created": [], "tool_result": launch}
        elif action == "browser.open_url":
            success = open_url_in_browser(plan.arguments["url"])
            result = {"response": "Opened the requested website." if success else "The URL was rejected or could not be opened.", "browser_info": None, "tasks_created": [], "tool_result": {"success": success}}
        elif action == "help":
            result = {"response": "I can safely inspect workspace context, manage tasks, research the web, open approved apps, summarize explicitly submitted writing, and organize notifications. Consequential actions require confirmation.", "tasks_created": [], "browser_info": None}
        else:
            state = plan.arguments.get("state") or {}
            app = state.get("active_app")
            suffix = f" Current workspace: {app}." if app else ""
            result = {"response": f"I can help turn that into tasks, research, or a safe workspace action.{suffix}", "tasks_created": [], "browser_info": None}
        result["plan"] = plan.to_dict()
        result.setdefault("status", "executed")
        return result
