import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from backend.db.db import get_session
from backend.db.models import StateSnapshot

logger = logging.getLogger("PlannerScheduler")

TICK_INTERVAL = 15                # seconds between planner checks
IDLE_SUGGESTION_THRESHOLD = 90     # seconds unchanged before suggesting related docs
MIN_ACTIVE_DURATION = 120          # must be focused this long before it "counts"
ABANDON_THRESHOLD = 300            # seconds backgrounded before a task proposal
WEB_AGENT_COOLDOWN = 600           # don't re-suggest for same context sooner than this

# Apps/domains we treat as "reading or writing" contexts worth suggesting research for
DOC_HINT_KEYWORDS = ["doc", "notion", "word", "google docs", "overleaf", "obsidian", "notes"]


class PlannerScheduler:
    """
    Resource-aware background planner. Runs on a timer, inspects current
    workspace state, and decides AT MOST one action per tick -- or none.
    Does not poll or invoke sub-agents unless a rule actually fires.
    """

    def __init__(self, coordinator):
        self.coordinator = coordinator  # reference to CoordinatorRouter singleton
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # In-memory context tracking (resets on restart -- fine for MVP)
        self._current_key = None
        self._contexts: Dict[Any, Dict[str, Any]] = {}
        self._last_web_agent_run: float = 0.0
        self._suggestions: List[Dict[str, Any]] = []
        self._suggestion_seq = 0
        self._last_decision = "idle"
        self._last_decision_at = None

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------
    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())
            logger.info("Planner scheduler started (tick=%ss)", TICK_INTERVAL)

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "last_decision": self._last_decision,
            "last_decision_at": self._last_decision_at,
            "tracked_contexts": len(self._contexts),
            "pending_suggestions": len([s for s in self._suggestions if not s["dismissed"]]),
        }

    def get_suggestions(self) -> List[Dict[str, Any]]:
        return [s for s in self._suggestions if not s["dismissed"]]

    def dismiss_suggestion(self, suggestion_id: int) -> bool:
        for s in self._suggestions:
            if s["id"] == suggestion_id:
                s["dismissed"] = True
                return True
        return False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    async def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception:
                logger.exception("Planner tick failed")
            await asyncio.sleep(TICK_INTERVAL)

    def _tick(self):
        latest = self._get_latest_snapshot()
        if latest is None:
            self._set_decision("no_state_data")
            return

        key = (latest.active_app, latest.browser_url or latest.active_window_title)
        now = time.time()

        # --- Track focus transitions ---
        if key != self._current_key:
            if self._current_key is not None and self._current_key in self._contexts:
                self._contexts[self._current_key]["left_at"] = now
            if key not in self._contexts:
                self._contexts[key] = {
                    "title": latest.active_window_title or latest.active_app,
                    "app": latest.active_app,
                    "url": latest.browser_url,
                    "started_at": now,
                    "left_at": None,
                    "task_created": False,
                }
            else:
                self._contexts[key]["left_at"] = None  # resumed
            self._current_key = key

        # --- Rule 2: abandoned tab/app -> task proposal (never auto-create) ---
        for ctx_key, ctx in list(self._contexts.items()):
            if ctx["task_created"] or ctx["left_at"] is None:
                continue
            was_active_long_enough = (ctx["left_at"] - ctx["started_at"]) >= MIN_ACTIVE_DURATION
            been_gone_long_enough = (now - ctx["left_at"]) >= ABANDON_THRESHOLD
            if was_active_long_enough and been_gone_long_enough:
                self._propose_abandoned_task(ctx)
                ctx["task_created"] = True
                self._set_decision(f"proposed_task_for:{ctx['title']}")
                return  # one action per tick

        # --- Rule 1: idle on same doc-like context -> web suggestion ---
        current_ctx = self._contexts.get(self._current_key)
        if current_ctx:
            unchanged_for = now - current_ctx["started_at"]
            cooldown_ok = (now - self._last_web_agent_run) >= WEB_AGENT_COOLDOWN
            looks_like_doc = self._looks_like_document_context(latest)
            if unchanged_for >= IDLE_SUGGESTION_THRESHOLD and cooldown_ok and looks_like_doc:
                self._trigger_web_suggestion(latest)
                self._last_web_agent_run = now
                self._set_decision(f"web_suggestion_for:{current_ctx['title']}")
                return

        self._set_decision("no_action")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_latest_snapshot(self) -> Optional[StateSnapshot]:
        with get_session() as session:
            return (
                session.query(StateSnapshot)
                .order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc())
                .first()
            )

    def _looks_like_document_context(self, snapshot: StateSnapshot) -> bool:
        haystack = " ".join(filter(None, [
            snapshot.active_app, snapshot.active_window_title,
            snapshot.browser_url, snapshot.browser_tab_title,
        ])).lower()
        return any(kw in haystack for kw in DOC_HINT_KEYWORDS) or bool(snapshot.browser_url)

    def _propose_abandoned_task(self, ctx: Dict[str, Any]):
        self._suggestion_seq += 1
        self._suggestions.append({
            "id": self._suggestion_seq,
            "kind": "task_proposal",
            "context": ctx["title"] or ctx["app"] or "Unfinished work",
            "response": "This context was left after sustained activity. Add a follow-up task only if it is still relevant.",
            "proposed_task": {"title": f"Follow up: {ctx['title'] or ctx['app'] or 'Unfinished work'}"},
            "created_at": datetime.utcnow().isoformat(),
            "dismissed": False,
        })
        logger.info("Proposed task for unattended context: %s", ctx["title"])

    def _trigger_web_suggestion(self, snapshot: StateSnapshot):
        query_text = snapshot.browser_tab_title or snapshot.active_window_title or snapshot.active_app
        if not query_text:
            return
        # Do not send window titles, URLs, or document context to a search provider automatically.
        # The UI presents this as a local suggestion; a user can then explicitly request research.
        self._suggestion_seq += 1
        self._suggestions.append({
            "id": self._suggestion_seq,
            "kind": "research_proposal",
            "context": query_text,
            "response": "You have been focused here for a while. Ask for research if related sources would be useful.",
            "created_at": datetime.utcnow().isoformat(),
            "dismissed": False,
        })

    def _set_decision(self, decision: str):
        self._last_decision = decision
        self._last_decision_at = datetime.utcnow().isoformat()
