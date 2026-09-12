"""Deterministic planner: it proposes actions but never performs them."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from backend.tools.os_tool import normalize_app_id

PlanCategory = Literal["observe", "assist", "hybrid", "consequential"]


@dataclass
class ExecutionPlan:
    intent: str
    category: PlanCategory
    action: str
    arguments: dict[str, Any] = field(default_factory=dict)
    confirmation_required: bool = False
    rationale: str = ""
    expected_result: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Planner:
    """Conservative intent planner. Unknown requests are assistance proposals, not actions."""

    _WAKE_PREFIX = re.compile(r"^(?:hey agent|hey assistant|agent[,!:])\s*", re.I)
    _COMPLETE = re.compile(r"(?:complete|done|finish|mark)\s+(?:task\s+)?#?(\d+)", re.I)

    def plan(self, request: str, state: dict[str, Any] | None = None) -> ExecutionPlan:
        query = self._WAKE_PREFIX.sub("", request.strip()) or request.strip()
        lower = query.lower()

        if not query:
            return ExecutionPlan("conversation", "observe", "help", rationale="No command was supplied.")
        if any(phrase in lower for phrase in ("what changed", "while i was away", "state diff", "what did i miss")):
            return ExecutionPlan("workspace_diff", "observe", "state.diff", rationale="The user requested workspace history.")
        if any(phrase in lower for phrase in ("what was i working", "current window", "active window", "what tab", "workspace state")):
            return ExecutionPlan("workspace_state", "observe", "state.latest", rationale="The user requested current workspace state.")
        if self._COMPLETE.search(lower):
            return ExecutionPlan("complete_task", "assist", "task.complete", {"task_id": int(self._COMPLETE.search(lower).group(1))}, rationale="The user explicitly requested task completion.")
        if any(phrase in lower for phrase in ("show task", "list task", "my task", "pending task", "what are my task")):
            return ExecutionPlan("list_tasks", "observe", "task.list", rationale="The user requested task state.")
        task_prefix = re.match(r"^(?:add(?: a)? task(?: to)?|create(?: a)? task(?: to)?|new task[:\s]*|remind me to)\s*(.*)$", query, re.I)
        if task_prefix:
            title = task_prefix.group(1).strip(" :.-")
            return ExecutionPlan("create_task", "assist", "task.create", {"title": title}, rationale="The user explicitly requested an internal task.")
        open_match = re.match(r"^(?:open|launch|start)\s+(?:my |the )?(.+?)\.?$", query, re.I)
        if open_match:
            target = open_match.group(1).strip()
            if target.lower() in {"this tab", "current tab", "active tab"}:
                if state and state.get("browser_url"):
                    return ExecutionPlan("open_current_tab", "assist", "browser.open_url", {"url": state["browser_url"]}, rationale="The user explicitly requested the active browser tab.")
                return ExecutionPlan(
                    "open_current_tab_unavailable", "observe", "conversation.respond",
                    {"response": "I do not have an active browser URL yet. In the Chrome companion, paste the API token and enable Active-tab metadata sync, then try again."},
                    rationale="Opening an unknown tab would be unsafe.",
                )
            app_id = normalize_app_id(target)
            if app_id:
                return ExecutionPlan("open_application", "assist", "desktop.open_app", {"app_id": app_id}, rationale="Requested application is allowlisted.", expected_result="Launch approved desktop application.")
            if re.match(r"https?://", target, re.I):
                return ExecutionPlan("open_website", "assist", "browser.open_url", {"url": target}, rationale="User supplied an HTTP(S) URL.")
        is_research = any(word in lower for word in ("search", "research", "compare", "look up", "find out", " vs "))
        if is_research:
            # An explicit research request opens Chrome with the search while local result collection continues.
            launch_browser = True
            cleaned = re.sub(r"(?i)\b(?:search|research|look up|find out|compare)\b", "", query).strip(" :.-")
            if cleaned.lower() in {"this current topic", "the current topic", "current topic", "this topic", "the topic"}:
                current_context = state or {}
                cleaned = (
                    current_context.get("browser_tab_title")
                    or current_context.get("active_window_title")
                    or current_context.get("active_app")
                    or cleaned
                )
            return ExecutionPlan("web_research", "hybrid", "web.research", {"query": cleaned or query, "launch_browser": launch_browser}, rationale="Research and summarisation are low-risk; external links remain user-controlled.")
        if any(word in lower for word in ("help", "what can you do", "commands", "features")):
            return ExecutionPlan("help", "observe", "help", rationale="The user requested capability guidance.")
        return ExecutionPlan("conversation", "observe", "conversation.respond", {"query": query, "state": state or {}}, rationale="No safe executable intent was identified.")
