"""Secure local API for the Digital Workspace Agent."""
from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import delete

from backend.core.config import settings
from backend.core.privacy import redact_sensitive_text, safe_excerpt
from backend.core.security import limit_request_size, require_api_token
from backend.coordinator.router import coordinator
from backend.coordinator.scheduler import PlannerScheduler
from backend.db.db import get_session, init_db
from backend.db.models import Notification, StateSnapshot, Task, WritingSuggestion, _is_agent_dashboard_url
from backend.tools.browser_tool import open_url_in_chrome
from backend.tools.os_tool import list_allowed_apps, normalize_app_id, open_desktop_app, open_terminal

planner_scheduler = PlannerScheduler(coordinator)


class SnapshotCreateRequest(BaseModel):
    active_app: str | None = Field(default=None, max_length=255)
    active_window_title: str | None = Field(default=None, max_length=500)
    browser_url: str | None = Field(default=None, max_length=1000)
    browser_tab_title: str | None = Field(default=None, max_length=500)
    captured_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None
    status: Literal["pending", "ongoing"] = "pending"


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    done: bool | None = None
    status: Literal["pending", "ongoing", "done"] | None = None
    due_at: datetime | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default_session", min_length=1, max_length=128)
    include_state: bool = True


class ConfirmationRequest(BaseModel):
    approved: bool


class BrowserOpenRequest(BaseModel):
    url: HttpUrl


class BrowserSummarizeRequest(BaseModel):
    url: HttpUrl
    title: str = Field(default="Web Page", max_length=500)
    content: str = Field(min_length=1, max_length=4000)
    consent: bool = False


class NotificationIngestRequest(BaseModel):
    source: str = Field(default="unknown", max_length=255)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(default="", max_length=2000)


class WritingAnalyzeRequest(BaseModel):
    url: str | None = Field(default=None, max_length=1000)
    title: str = Field(default="Untitled", max_length=500)
    text: str = Field(min_length=1, max_length=2000)
    operation: Literal["summarize", "improve", "explain", "ideas"] = "summarize"
    consent: bool = False


class AppLaunchRequest(BaseModel):
    app_id: str = Field(min_length=1, max_length=32)


def _prune_expired_data() -> None:
    now = datetime.utcnow()
    with get_session() as session:
        session.execute(delete(StateSnapshot).where(StateSnapshot.captured_at < now - timedelta(days=settings.snapshot_retention_days)))
        session.execute(delete(Notification).where(Notification.created_at < now - timedelta(days=settings.content_retention_days)))
        session.execute(delete(WritingSuggestion).where(WritingSuggestion.created_at < now - timedelta(days=settings.content_retention_days)))
        session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_runtime()
    init_db()
    _prune_expired_data()
    planner_scheduler.start()
    yield
    planner_scheduler.stop()


app = FastAPI(title="Digital Workspace Agent API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Workspace-Token"],
)
app.middleware("http")(limit_request_size)
app.mount("/word-addin", StaticFiles(directory="system-agent/word-addin"), name="word-addin")


@app.get("/health")
def health_check():
    return {"status": "ok", "mode": "local-authenticated", "timestamp": datetime.now(timezone.utc).isoformat()}


api = APIRouter(prefix="/api", dependencies=[Depends(require_api_token)])


@api.post("/chat")
def chat_with_coordinator(payload: ChatRequest):
    return coordinator.handle_message(payload.message, payload.session_id, payload.include_state)


@api.post("/actions/{confirmation_id}/confirm")
def confirm_action(confirmation_id: str, payload: ConfirmationRequest):
    return coordinator.confirm_action(confirmation_id, payload.approved)


@api.post("/snapshot", status_code=status.HTTP_201_CREATED)
def create_state_snapshot(payload: SnapshotCreateRequest):
    captured_at = payload.captured_at or datetime.utcnow()
    with get_session() as session:
        snapshot = StateSnapshot(
            active_app=payload.active_app,
            active_window_title=payload.active_window_title,
            browser_url=payload.browser_url,
            browser_tab_title=payload.browser_tab_title,
            captured_at=captured_at,
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        return {"status": "success", "snapshot": snapshot.to_dict()}


@api.get("/snapshot/latest")
def get_latest_state_snapshot():
    with get_session() as session:
        snapshot = session.query(StateSnapshot).order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc()).first()
        return snapshot.to_dict() if snapshot else None


@api.get("/workspace/overview")
def workspace_overview():
    """One bounded read for the dashboard/widget, avoiding noisy polling bursts."""
    with get_session() as session:
        snapshot = session.query(StateSnapshot).order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc()).first()
        tasks = session.query(Task).order_by(Task.created_at.desc()).all()
        notifications = session.query(Notification).filter(Notification.reviewed == False).order_by(Notification.created_at.desc()).all()
        writing = session.query(WritingSuggestion).filter(WritingSuggestion.reviewed == False).order_by(WritingSuggestion.created_at.desc()).all()
        return {
            "snapshot": snapshot.to_dict() if snapshot else None,
            "tasks": [task.to_dict() for task in tasks],
            "notifications": [note.to_dict() for note in notifications],
            "writing_suggestions": [item.to_dict() for item in writing],
            "planner": {"status": planner_scheduler.get_status(), "suggestions": planner_scheduler.get_suggestions()},
            "settings": _public_settings(),
        }


@api.get("/snapshot/diff")
def get_snapshot_diff(limit: int = Query(5, ge=2, le=20)):
    return coordinator.state_agent.diff_snapshots(limit=limit)


@api.get("/snapshot/history")
def get_snapshot_history(limit: int = Query(20, ge=1, le=100)):
    with get_session() as session:
        snapshots = session.query(StateSnapshot).order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc()).limit(limit).all()
        return [snapshot.to_dict() for snapshot in snapshots]


@api.delete("/snapshot/history")
def delete_snapshot_history():
    with get_session() as session:
        deleted = session.query(StateSnapshot).delete()
        session.commit()
    return {"status": "deleted", "count": deleted}


@api.get("/tasks")
def list_tasks(done: bool | None = None, task_status: Literal["pending", "ongoing", "done"] | None = None):
    with get_session() as session:
        query = session.query(Task)
        if done is not None:
            query = query.filter(Task.done == done)
        if task_status:
            query = query.filter(Task.status == task_status)
        return [task.to_dict() for task in query.order_by(Task.created_at.desc()).all()]


@api.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreateRequest):
    context = coordinator.state_agent.get_latest_task_context() or {}
    with get_session() as session:
        task = Task(
            title=payload.title,
            description=payload.description,
            due_at=payload.due_at,
            status=payload.status,
            done=False,
            source_url=context.get("browser_url") or None,
            source_app=context.get("active_app") or None,
            source_title=context.get("browser_tab_title") or context.get("active_window_title") or None,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return task.to_dict()


@api.post("/tasks/{task_id}/navigate")
def navigate_to_task_context(task_id: int):
    """Reopen the app or browser tab captured when a task was created."""
    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        source_url, source_app, source_title = task.source_url, task.source_app, task.source_title
    if _is_agent_dashboard_url(source_url):
        raise HTTPException(status_code=409, detail="This task was linked to the agent dashboard, not its original work. Focus the correct app or tab and choose Link current app/tab.")
    if source_url and source_url.startswith(("https://", "http://")):
        success = open_url_in_chrome(source_url, bring_to_front=True)
        if success:
            return {"status": "opened", "target": "browser", "source_title": source_title, "url": source_url}
    app_id = normalize_app_id(source_app or "")
    if app_id:
        launch = open_desktop_app(app_id)
        if launch.get("success"):
            return {"status": "opened", "target": "app", "source_title": source_title, "app": launch.get("app")}
    raise HTTPException(status_code=409, detail="This task has no reopenable app or HTTP(S) tab context. Create it while the relevant workspace is active.")


@api.post("/tasks/{task_id}/link-current-context")
def link_task_to_current_context(task_id: int):
    """Explicitly attach an older task to the workspace currently in focus."""
    context = coordinator.state_agent.get_latest_task_context() or {}
    if not context.get("browser_url") and not context.get("active_app"):
        raise HTTPException(status_code=409, detail="No current workspace context is available to link.")
    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.source_url = context.get("browser_url") or None
        task.source_app = context.get("active_app") or None
        task.source_title = context.get("browser_tab_title") or context.get("active_window_title") or None
        session.commit()
        session.refresh(task)
        return task.to_dict()


@api.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdateRequest):
    with get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        for field in ("title", "description", "due_at"):
            value = getattr(payload, field)
            if value is not None:
                setattr(task, field, value)
        if payload.status is not None:
            task.status = payload.status
            task.done = payload.status == "done"
        if payload.done is not None:
            task.done = payload.done
            task.status = "done" if payload.done else ("pending" if task.status == "done" else task.status)
        session.commit()
        session.refresh(task)
        return task.to_dict()


@api.get("/apps")
def approved_apps():
    return list_allowed_apps()


@api.post("/os/app")
def launch_desktop_app(payload: AppLaunchRequest):
    return open_desktop_app(payload.app_id)


@api.post("/os/terminal")
def launch_terminal():
    return open_terminal()


@api.post("/browser/open")
def open_browser(payload: BrowserOpenRequest):
    url = str(payload.url)
    success = open_url_in_chrome(url, bring_to_front=True)
    return {"status": "success" if success else "failed", "url": url}


@api.post("/browser/summarize")
def summarize_browser_tab(payload: BrowserSummarizeRequest):
    if not payload.consent:
        raise HTTPException(status_code=403, detail="Explicit content consent is required")
    clean_text = redact_sensitive_text(payload.content, limit=4000)
    sentences = [part.strip() for part in clean_text.replace("\n", " ").split(".") if len(part.strip()) > 20]
    summary = ". ".join(sentences[:2]) or f"Reviewing {payload.title}."
    return {
        "success": True,
        "url": str(payload.url),
        "title": payload.title,
        "work_context": "Explicit browser-page summary",
        "summary": summary,
        "key_takeaways": sentences[2:5] or ["No additional local takeaways were identified."],
        "external_processing": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _writing_suggestion(text: str, operation: str) -> str:
    clean_text = re.sub(r"\s+", " ", text).strip()
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean_text) if part.strip()]
    if operation == "improve":
        replacements = {
            "in order to": "to",
            "due to the fact that": "because",
            "at this point in time": "now",
            "a number of": "several",
            "has the ability to": "can",
        }
        revised = clean_text
        for original, replacement in replacements.items():
            revised = re.sub(rf"\b{re.escape(original)}\b", replacement, revised, flags=re.IGNORECASE)
        if revised and revised[-1] not in ".!?":
            revised += "."
        long_sentence_count = sum(len(sentence.split()) > 28 for sentence in sentences)
        focus = "Break the longest sentence into two ideas." if long_sentence_count else "Keep one main idea in each sentence."
        return f"Suggested local rewrite:\n{revised}\n\nImprovement note: {focus}"
    if operation == "explain":
        return f"Local explanation: the passage is primarily about {sentences[0][:180] if sentences else 'the submitted text'}."
    if operation == "ideas":
        return "Local ideas: add a concrete example, state the intended outcome, and list one question the reader should be able to answer."
    return ". ".join(sentences[:2])[:500] or "No summary could be produced from the submitted text."


_KEYWORD_STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been", "being", "between", "could", "does", "from", "have", "into", "more", "most", "not", "only", "other", "should", "some", "such", "than", "that", "their", "there", "these", "they", "this", "those", "through", "using", "very", "what", "when", "where", "which", "with", "would", "your",
}


def _writing_research_topics(text: str, title: str) -> dict[str, Any]:
    """Derive compact local search terms from explicitly submitted text only."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text.lower())
    keywords: list[str] = []
    for word in words:
        if word in _KEYWORD_STOPWORDS or word in keywords:
            continue
        keywords.append(word)
        if len(keywords) == 5:
            break
    topic = " ".join(keywords[:3])
    if not topic and title.lower() not in {"untitled", "microsoft word selection"}:
        topic = title[:120]
    queries = []
    if topic:
        queries = [
            {"label": f"{topic} documentation", "query": f"{topic} documentation"},
            {"label": f"{topic} examples", "query": f"{topic} examples"},
            {"label": f"{topic} best practices", "query": f"{topic} best practices"},
        ]
    return {"keywords": keywords, "related_queries": queries}


@api.post("/writing/analyze", status_code=status.HTTP_201_CREATED)
def analyze_writing(payload: WritingAnalyzeRequest):
    if not payload.consent:
        raise HTTPException(status_code=403, detail="Writing analysis requires explicit consent")
    redacted = redact_sensitive_text(payload.text, limit=2000)
    suggestion_text = _writing_suggestion(redacted, payload.operation)
    research_topics = _writing_research_topics(redacted, payload.title)
    with get_session() as session:
        suggestion = WritingSuggestion(
            source_url=payload.url,
            source_title=payload.title,
            excerpt=safe_excerpt(redacted),
            suggestion_text=suggestion_text,
            related_links=json.dumps(research_topics),
            reviewed=False,
        )
        session.add(suggestion)
        session.commit()
        session.refresh(suggestion)
        return suggestion.to_dict()


@api.get("/writing/suggestions")
def list_writing_suggestions(reviewed: bool | None = None):
    with get_session() as session:
        query = session.query(WritingSuggestion)
        if reviewed is not None:
            query = query.filter(WritingSuggestion.reviewed == reviewed)
        return [item.to_dict() for item in query.order_by(WritingSuggestion.created_at.desc()).all()]


@api.patch("/writing/suggestions/{suggestion_id}/review")
def mark_writing_suggestion_reviewed(suggestion_id: int):
    with get_session() as session:
        item = session.get(WritingSuggestion, suggestion_id)
        if not item:
            raise HTTPException(status_code=404, detail="Writing suggestion not found")
        item.reviewed = True
        session.commit()
        return item.to_dict()


@api.delete("/writing/suggestions/{suggestion_id}")
def delete_writing_suggestion(suggestion_id: int):
    with get_session() as session:
        item = session.get(WritingSuggestion, suggestion_id)
        if not item:
            raise HTTPException(status_code=404, detail="Writing suggestion not found")
        session.delete(item)
        session.commit()
    return {"status": "deleted", "id": suggestion_id}


@api.post("/notifications", status_code=status.HTTP_201_CREATED)
def ingest_notification(payload: NotificationIngestRequest):
    content = redact_sensitive_text(payload.content, limit=2000)
    summary = (content.split(".")[0].strip() or payload.title)[:300]
    with get_session() as session:
        note = Notification(source=payload.source, raw_title=safe_excerpt(payload.title, 500), raw_content=content, summary=summary, reviewed=False)
        session.add(note)
        session.commit()
        session.refresh(note)
        return note.to_dict()


@api.get("/notifications")
def list_notifications(reviewed: bool | None = None):
    with get_session() as session:
        query = session.query(Notification)
        if reviewed is not None:
            query = query.filter(Notification.reviewed == reviewed)
        return [note.to_dict() for note in query.order_by(Notification.created_at.desc()).all()]


@api.patch("/notifications/{notification_id}/review")
def mark_notification_reviewed(notification_id: int):
    with get_session() as session:
        note = session.get(Notification, notification_id)
        if not note:
            raise HTTPException(status_code=404, detail="Notification not found")
        note.reviewed = True
        session.commit()
        return note.to_dict()


@api.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int):
    with get_session() as session:
        note = session.get(Notification, notification_id)
        if not note:
            raise HTTPException(status_code=404, detail="Notification not found")
        session.delete(note)
        session.commit()
    return {"status": "deleted", "id": notification_id}


@api.get("/planner/status")
def planner_status():
    return planner_scheduler.get_status()


@api.get("/planner/suggestions")
def planner_suggestions():
    return planner_scheduler.get_suggestions()


@api.post("/planner/suggestions/{suggestion_id}/dismiss")
def dismiss_planner_suggestion(suggestion_id: int):
    if not planner_scheduler.dismiss_suggestion(suggestion_id):
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return {"status": "dismissed", "id": suggestion_id}


def _public_settings():
    return {"capture_enabled": settings.capture_enabled, "external_llm_enabled": settings.allow_external_llm, "retention": {"snapshots_days": settings.snapshot_retention_days, "content_days": settings.content_retention_days}}


@api.get("/settings")
def public_settings():
    return _public_settings()


app.include_router(api)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.backend_host, port=settings.backend_port, reload=False)
