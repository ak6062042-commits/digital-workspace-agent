"""Compatibility facade for the explicit State -> Planner -> Executor flow."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.coordinator.context_store import context_store
from backend.orchestration.executor import Executor
from backend.orchestration.planner import Planner


class CoordinatorRouter:
    """Coordinates context, planning, and controlled execution; it is not a tool itself."""

    def __init__(self) -> None:
        self.planner = Planner()
        self.executor = Executor()
        # Compatibility attributes used by existing endpoints and scheduler.
        self.state_agent = self.executor.state_agent
        self.task_agent = self.executor.task_agent
        self.web_agent = self.executor.web_agent

    def handle_message(self, message: str, session_id: str = "default_session", include_state: bool = True) -> dict[str, Any]:
        state = self.state_agent.get_latest_snapshot() if include_state else None
        context_store.add_message(session_id, "user", message)
        plan = self.planner.plan(message, state)
        result = self.executor.execute_or_propose(plan)
        response = result.get("response", "No response generated.")
        context_store.add_message(session_id, "assistant", response, metadata={"plan": plan.to_dict()})
        return {
            "response": response,
            "routed_agent": plan.action.split(".")[0],
            "tasks_created": result.get("tasks_created", []),
            "tasks_modified": result.get("tasks_modified", []),
            "browser_info": result.get("browser_info"),
            "state_snapshot": state or result.get("state_snapshot"),
            "plan": plan.to_dict(),
            "confirmation_id": result.get("confirmation_id"),
            "status": result.get("status", "executed"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def confirm_action(self, confirmation_id: str, approved: bool) -> dict[str, Any]:
        return self.executor.confirm(confirmation_id, approved)


coordinator = CoordinatorRouter()
