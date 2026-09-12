import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from backend.db.db import get_session
from backend.db.models import StateSnapshot

logger = logging.getLogger("DigitalStateAgent")


class DigitalStateAgent:
    """
    Digital State Agent that queries and diffs OS and browser snapshots.
    Answers:
      - "What was I working on?"
      - "What changed while I was away?"
      - "What browser tabs did I have open?"
    """

    @staticmethod
    def _format_time_ago(dt: datetime) -> str:
        """Helper to format relative time ago."""
        now = datetime.utcnow()
        diff = (now - dt).total_seconds()
        if diff < 60:
            return f"{int(max(1, diff))} seconds ago"
        elif diff < 3600:
            return f"{int(diff // 60)} minutes ago"
        elif diff < 86400:
            return f"{int(diff // 3600)} hours ago"
        return f"{int(diff // 86400)} days ago"

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """Fetch the most recent snapshot."""
        with get_session() as session:
            snap = (
                session.query(StateSnapshot)
                .order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc())
                .first()
            )
            return snap.to_dict() if snap else None

    @staticmethod
    def _is_agent_control_surface(snapshot: StateSnapshot) -> bool:
        """Do not bind tasks to the dashboard, Word add-in, or PyQt widget."""
        url = snapshot.browser_url or ""
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        app = (snapshot.active_app or "").lower()
        title = (snapshot.active_window_title or "").lower()
        return (
            (host in {"localhost", "127.0.0.1"} and (parsed.port == 5173 or parsed.path.startswith("/word-addin")))
            or ("python" in app and "digital workspace command center" in title)
        )

    def get_latest_task_context(self) -> Optional[Dict[str, Any]]:
        """Return the latest real app/tab, skipping the agent's own UI surfaces."""
        with get_session() as session:
            snapshots = (
                session.query(StateSnapshot)
                .order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc())
                .limit(20)
                .all()
            )
            for snapshot in snapshots:
                if not self._is_agent_control_surface(snapshot):
                    return snapshot.to_dict()
        # Do not fall back to the dashboard/widget when it is the only recent
        # state.  Saving that URL would make a task reopen the agent instead of
        # the user's actual work.
        return None

    def diff_snapshots(self, limit: int = 5) -> Dict[str, Any]:
        """
        Analyze transitions across the last N snapshots to determine what changed.
        """
        with get_session() as session:
            snaps = (
                session.query(StateSnapshot)
                .order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc())
                .limit(limit)
                .all()
            )

        if not snaps or len(snaps) < 2:
            return {
                "summary": "Insufficient snapshot history to compute changes. Keep the local agent running to record transitions.",
                "transitions": [],
                "current": snaps[0].to_dict() if snaps else None
            }

        transitions = []
        for i in range(len(snaps) - 1):
            curr = snaps[i]
            prev = snaps[i + 1]

            changes = []
            if curr.active_app != prev.active_app:
                changes.append(f"Switched app from **{prev.active_app or 'Unknown'}** to **{curr.active_app or 'Unknown'}**")
            if curr.active_window_title != prev.active_window_title:
                changes.append(f"Window changed to *\"{curr.active_window_title or 'Untitled'}\"*")
            if curr.browser_url != prev.browser_url and curr.browser_url:
                changes.append(f"Navigated browser to `{curr.browser_url}`")

            if changes:
                transitions.append({
                    "timestamp": curr.captured_at.isoformat() if curr.captured_at else "",
                    "time_ago": self._format_time_ago(curr.captured_at) if curr.captured_at else "",
                    "changes": changes
                })

        return {
            "summary": f"Detected {len(transitions)} workspace transition(s) recently.",
            "transitions": transitions,
            "current": snaps[0].to_dict()
        }

    def handle(self, query: str) -> Dict[str, Any]:
        """Process natural language digital state inquiry."""
        q_lower = query.lower()

        # Check for diff / "what changed while I was away"
        if any(phrase in q_lower for phrase in ["what changed", "while i was away", "state diff", "what did i miss", "changes"]):
            diff_res = self.diff_snapshots(limit=6)
            if not diff_res["transitions"]:
                msg = (
                    "**Workspace State Diff**:\n\n"
                    "No major context shifts detected while you were away. "
                    f"You are still focused in **{diff_res['current']['active_app'] or 'your desktop'}**."
                )
            else:
                change_lines = []
                for t in diff_res["transitions"][:4]:
                    for c in t["changes"]:
                        change_lines.append(f"- *({t['time_ago']})* {c}")
                msg = (
                    f"**Here is what shifted across your workspace:**\n\n"
                    + "\n".join(change_lines)
                )

            return {
                "agent": "state_agent",
                "response": msg,
                "state_snapshot": diff_res["current"],
                "tasks_created": []
            }

        # Standard "what was I working on" / current state
        latest = self.get_latest_snapshot()
        if not latest:
            return {
                "agent": "state_agent",
                "response": "No workspace snapshots captured yet. Start the local agent (`python system-agent/local-agent/watcher.py`) to begin streaming OS context.",
                "state_snapshot": None,
                "tasks_created": []
            }

        app_name = latest.get("active_app") or "Unknown Application"
        win_title = latest.get("active_window_title") or "Untitled Window"
        url = latest.get("browser_url")
        tab_title = latest.get("browser_tab_title")

        response_lines = [
            f"You were actively working in **{app_name}** on window: *\"{win_title}\"*."
        ]

        if url:
            response_lines.append(f"Active browser tab: [{tab_title or url}]({url})")

        from backend.coordinator.context_store import context_store
        browser_summary = context_store.get_browser_summary()
        if browser_summary and (not url or browser_summary.get("url") == url):
            if browser_summary.get("work_context"):
                response_lines.append(f"\n🧠 **AI Page Intelligence** ({browser_summary.get('work_context')}):")
            else:
                response_lines.append("\n🧠 **AI Page Intelligence**:")
            if browser_summary.get("summary"):
                response_lines.append(f"> {browser_summary.get('summary')}")

        response_lines.append("\nYour workspace context is synced and live.")

        return {
            "agent": "state_agent",
            "response": "\n".join(response_lines),
            "state_snapshot": latest,
            "tasks_created": []
        }
