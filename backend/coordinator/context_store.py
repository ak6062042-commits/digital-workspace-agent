import time
from typing import Dict, List, Any, Optional
from collections import defaultdict


class ContextStore:
    """
    Session context store keeping conversation memory and attached workspace state.
    """

    def __init__(self, max_history_per_session: int = 20):
        self.max_history = max_history_per_session
        self.sessions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.cached_state: Dict[str, Any] = {}
        self.cached_browser_summary: Optional[Dict[str, Any]] = None

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Record a chat message in the session history."""
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        self.sessions[session_id].append(entry)
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history:]

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history for a given session."""
        return self.sessions.get(session_id, [])

    def clear_session(self, session_id: str):
        """Reset history for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def set_active_state(self, snapshot: Dict[str, Any]):
        """Update the latest cached workspace snapshot."""
        self.cached_state = snapshot

    def get_active_state(self) -> Optional[Dict[str, Any]]:
        """Retrieve current cached workspace state."""
        return self.cached_state or None

    def set_browser_summary(self, summary: Dict[str, Any]):
        """Store semantic summary from browser companion."""
        self.cached_browser_summary = summary

    def get_browser_summary(self) -> Optional[Dict[str, Any]]:
        """Retrieve latest semantic browser summary."""
        return self.cached_browser_summary


# Global singleton instance
context_store = ContextStore()
