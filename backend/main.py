import os
import sys
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is in python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.db.db import init_db, get_session
from backend.db.models import StateSnapshot, Task, Notification, WritingSuggestion
from backend.coordinator.router import coordinator

from backend.coordinator.scheduler import PlannerScheduler

planner = PlannerScheduler(coordinator)


# Pydantic Request/Response Models
class SnapshotCreateRequest(BaseModel):
    active_app: Optional[str] = None
    active_window_title: Optional[str] = None
    browser_url: Optional[str] = None
    browser_tab_title: Optional[str] = None
    captured_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    due_at: Optional[datetime] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None
    due_at: Optional[datetime] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = "default_session"
    include_state: Optional[bool] = True


class NotificationIngestRequest(BaseModel):
    source: Optional[str] = "unknown"
    title: str = Field(..., min_length=1)
    content: Optional[str] = ""

class WritingAnalyzeRequest(BaseModel):
    url: str
    title: Optional[str] = "Untitled"
    text: str = Field(..., min_length=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    planner.start()
    yield
    planner.stop()

app = FastAPI(
    title="Digital Workspace Agent API",
    description="Backend API supporting Coordinator AI, State Agent, Task Agent, Web Research Agent, and Frontend.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend and browser extensions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ============================================================================
# Track A & Coordinator: AI Chat & Agent Routing
# ============================================================================

@app.post("/api/chat")
def chat_with_coordinator(payload: ChatRequest):
    """
    Direct user query to the Coordinator Agent which routes to:
    - task_agent (task management)
    - state_agent (what was I working on / what changed)
    - web_agent (search + fetch research)
    - coordinator (general help)
    """
    result = coordinator.handle_message(
        message=payload.message,
        session_id=payload.session_id or "default_session",
        include_state=payload.include_state if payload.include_state is not None else True,
    )
    return result


# ============================================================================
# Track C: State Snapshot & Diff Endpoints
# ============================================================================

@app.post("/api/snapshot", status_code=status.HTTP_201_CREATED)
def create_state_snapshot(payload: SnapshotCreateRequest):
    """
    Ingest a new OS / browser state snapshot from the local agent or browser extension.
    """
    captured_dt = None
    if payload.captured_at:
        try:
            captured_dt = datetime.fromisoformat(payload.captured_at.replace("Z", "+00:00"))
        except Exception:
            captured_dt = datetime.utcnow()
    else:
        captured_dt = datetime.utcnow()

    with get_session() as session:
        snapshot = StateSnapshot(
            active_app=payload.active_app,
            active_window_title=payload.active_window_title,
            browser_url=payload.browser_url,
            browser_tab_title=payload.browser_tab_title,
            captured_at=captured_dt,
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        return {"status": "success", "snapshot": snapshot.to_dict()}


@app.get("/api/snapshot/latest")
def get_latest_state_snapshot():
    """
    Retrieve the most recent state snapshot recorded in the database.
    """
    with get_session() as session:
        snapshot = (
            session.query(StateSnapshot)
            .order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc())
            .first()
        )
        if not snapshot:
            return None
        return snapshot.to_dict()


@app.get("/api/snapshot/diff")
def get_snapshot_diff(limit: int = Query(5, ge=2, le=20)):
    """
    Compute workspace state transitions across the last N snapshots.
    """
    return coordinator.state_agent.diff_snapshots(limit=limit)


@app.get("/api/snapshot/history")
def get_snapshot_history(limit: int = Query(20, ge=1, le=100)):
    """
    Retrieve a historical list of recent state snapshots.
    """
    with get_session() as session:
        snapshots = (
            session.query(StateSnapshot)
            .order_by(StateSnapshot.captured_at.desc(), StateSnapshot.id.desc())
            .limit(limit)
            .all()
        )
        return [s.to_dict() for s in snapshots]


# ============================================================================
# Task Management Endpoints
# ============================================================================

@app.get("/api/tasks")
def list_tasks(done: Optional[bool] = None):
    """
    List tasks, optionally filtered by completion status.
    """
    with get_session() as session:
        query = session.query(Task)
        if done is not None:
            query = query.filter(Task.done == done)
        tasks = query.order_by(Task.created_at.desc()).all()
        return [t.to_dict() for t in tasks]


@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreateRequest):
    """
    Create a new task in the database.
    """
    with get_session() as session:
        task = Task(
            title=payload.title,
            description=payload.description,
            due_at=payload.due_at,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return task.to_dict()


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdateRequest):
    """
    Update or toggle task completion.
    """
    with get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = payload.description
        if payload.done is not None:
            task.done = payload.done
        if payload.due_at is not None:
            task.due_at = payload.due_at

        session.commit()
        session.refresh(task)
        return task.to_dict()


# ============================================================================
# Desktop Browser Control Endpoints
# ============================================================================

class BrowserOpenRequest(BaseModel):
    url: str = Field(..., min_length=1)

@app.post("/api/browser/open")
def open_browser(payload: BrowserOpenRequest):
    """
    Directly launch or navigate the desktop browser to a given URL.
    """
    from backend.tools.browser_tool import open_url_in_browser
    success = open_url_in_browser(payload.url, bring_to_front=True)
    return {"status": "success" if success else "failed", "url": payload.url}


# ============================================================================
# Browser Companion AI Intelligence
# ============================================================================

class BrowserSummarizeRequest(BaseModel):
    url: str
    title: Optional[str] = "Web Page"
    content: Optional[str] = ""

@app.post("/api/browser/summarize")
def summarize_browser_tab(payload: BrowserSummarizeRequest):
    """
    Synthesize active webpage content using AI.
    Extracts high-level work context, key takeaways, and suggested actionable tasks.
    Attaches to the active coordinator context store for seamless recall.
    """
    import re
    import json
    from backend.coordinator.context_store import context_store

    clean_text = (payload.content or "").strip()[:4000]
    title = payload.title or "Untitled Page"
    url = payload.url or ""

    # 1. Deduce topic from title and domain
    domain = url.split("//")[-1].split("/")[0].replace("www.", "") if "//" in url else "web"
    sentences = [s.strip() for s in re.split(r'[.\n]+', clean_text) if len(s.strip()) > 20]
    
    summary_sentences = sentences[:2] if len(sentences) >= 2 else sentences[:1]
    summary_text = " ".join(summary_sentences) if summary_sentences else f"Actively reviewing {title}."

    # Infer domain category
    lower_title = (title + " " + clean_text[:600]).lower()
    if any(k in lower_title for k in ["api", "doc", "endpoint", "sdk", "reference"]):
        work_cat = "API & SDK Documentation"
    elif any(k in lower_title for k in ["react", "vue", "frontend", "css", "html", "javascript", "typescript", "tailwind"]):
        work_cat = "Frontend Architecture"
    elif any(k in lower_title for k in ["python", "fastapi", "docker", "kubernetes", "backend", "db", "database", "sql"]):
        work_cat = "Backend & Systems Infrastructure"
    elif any(k in lower_title for k in ["github", "pr", "commit", "pull request", "merge", "branch"]):
        work_cat = "Code Review & Version Control"
    elif any(k in lower_title for k in ["price", "pricing", "plan", "billing", "tier"]):
        work_cat = "Tool Pricing & Comparison"
    else:
        work_cat = f"Technical Research ({domain})"

    key_takeaways = [s for s in sentences[1:4]] if len(sentences) > 2 else [f"Focused on {title}"]
    suggested_task = f"Implement patterns from {title[:35]}"

    # Try fast LLM if available in environment
    llm_api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY")
    if llm_api_key:
        try:
            from openai import OpenAI
            base_url = "https://api.groq.com/openai/v1" if os.environ.get("GROQ_API_KEY") else None
            api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
            model = "llama-3.1-8b-instant" if os.environ.get("GROQ_API_KEY") else "gpt-4o-mini"
            client = OpenAI(api_key=api_key, base_url=base_url)
            json_format_instruction = '{"work_context": string, "summary": string, "key_takeaways": [string], "suggested_task": string}'
            user_prompt = f"URL: {url}\nTitle: {title}\nContent:\n{clean_text}\n\nRespond with a JSON object: {json_format_instruction}"
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a workspace research AI. Summarize the given webpage content for a developer assistant."},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=300
            )
            parsed = json.loads(resp.choices[0].message.content)
            work_cat = parsed.get("work_context", work_cat)
            summary_text = parsed.get("summary", summary_text)
            key_takeaways = parsed.get("key_takeaways", key_takeaways)
            suggested_task = parsed.get("suggested_task", suggested_task)
        except Exception:
            pass

    result = {
        "success": True,
        "url": url,
        "title": title,
        "work_context": work_cat,
        "summary": summary_text,
        "key_takeaways": key_takeaways,
        "suggested_task": suggested_task,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Store in context store for the Digital State Agent
    context_store.set_browser_summary(result)

    return result


# ============================================================================
# Desktop OS & Terminal Control Endpoints
# ============================================================================

class AppLaunchRequest(BaseModel):
    app_name: str = Field(..., min_length=1)

@app.post("/api/os/terminal")
def launch_terminal():
    """
    Launch native desktop Terminal on macOS.
    """
    from backend.tools.os_tool import open_terminal
    res = open_terminal()
    return res

@app.post("/api/os/app")
def launch_desktop_app(payload: AppLaunchRequest):
    """
    Launch native desktop application (VS Code, Finder, Calculator, Notes, etc.)
    """
    from backend.tools.os_tool import open_desktop_app
    res = open_desktop_app(payload.app_name)
    return res


# ============================================================================
# Demo Utility Endpoints
# ============================================================================

@app.post("/api/demo/seed")
def reseed_demo_data():
    """
    Seed fresh demo tasks and snapshots for hackathon presentations.
    """
    from scripts.seed_data import seed
    seed()
    return {"status": "success", "message": "Demo data refreshed"}

# ============================================================================
# Planner / Scheduler Endpoints
# ============================================================================

@app.get("/api/planner/status")
def planner_status():
    return planner.get_status()


@app.get("/api/planner/suggestions")
def planner_suggestions():
    return planner.get_suggestions()


@app.post("/api/planner/suggestions/{suggestion_id}/dismiss")
def dismiss_planner_suggestion(suggestion_id: int):
    ok = planner.dismiss_suggestion(suggestion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return {"status": "dismissed", "id": suggestion_id}

# ============================================================================
# Notification Queue Endpoints
# ============================================================================

def _summarize_notification(title: str, content: str) -> str:
    text = (content or "").strip()
    if not text:
        return title
    first_sentence = text.split(".")[0].strip()
    if len(first_sentence) > 140:
        first_sentence = first_sentence[:140].rstrip() + "..."
    return first_sentence or title


@app.post("/api/notifications", status_code=status.HTTP_201_CREATED)
def ingest_notification(payload: NotificationIngestRequest):
    """
    Accepts a raw notification, summarizes it, and queues it for later review.
    """
    summary = _summarize_notification(payload.title, payload.content or "")
    with get_session() as session:
        note = Notification(
            source=payload.source,
            raw_title=payload.title,
            raw_content=payload.content,
            summary=summary,
            reviewed=False,
        )
        session.add(note)
        session.commit()
        session.refresh(note)
        return note.to_dict()


@app.get("/api/notifications")
def list_notifications(reviewed: Optional[bool] = None):
    with get_session() as session:
        query = session.query(Notification)
        if reviewed is not None:
            query = query.filter(Notification.reviewed == reviewed)
        notes = query.order_by(Notification.created_at.desc()).all()
        return [n.to_dict() for n in notes]


@app.patch("/api/notifications/{notification_id}/review")
def mark_notification_reviewed(notification_id: int):
    with get_session() as session:
        note = session.query(Notification).filter(Notification.id == notification_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Notification not found")
        note.reviewed = True
        session.commit()
        session.refresh(note)
        return note.to_dict()

# ============================================================================
# Writing Assist Endpoints
# ============================================================================

@app.post("/api/writing/analyze", status_code=status.HTTP_201_CREATED)
def analyze_writing(payload: WritingAnalyzeRequest):
    """
    Accepts a snapshot of actively-typed text, searches for related resources,
    and queues a suggestion for later review (never interrupts the user).
    """
    import json as _json

    text = payload.text.strip()
    excerpt = text[:300]
    topic_words = " ".join(text.split()[:12])
    query = topic_words or (payload.title or "this topic")

    related_links = None
    suggestion_text = f'You\'re writing about: "{topic_words[:80]}"'

    try:
        agent_result = coordinator.web_agent.handle(f"related resources for {query}")
        browser_info = agent_result.get("browser_info")
        response_text = agent_result.get("response", "")
        if browser_info:
            related_links = _json.dumps(browser_info)
        if response_text:
            suggestion_text = response_text[:500]
    except Exception:
        pass

    with get_session() as session:
        suggestion = WritingSuggestion(
            source_url=payload.url,
            source_title=payload.title,
            excerpt=excerpt,
            suggestion_text=suggestion_text,
            related_links=related_links,
            reviewed=False,
        )
        session.add(suggestion)
        session.commit()
        session.refresh(suggestion)
        return suggestion.to_dict()


@app.get("/api/writing/suggestions")
def list_writing_suggestions(reviewed: Optional[bool] = None):
    with get_session() as session:
        query = session.query(WritingSuggestion)
        if reviewed is not None:
            query = query.filter(WritingSuggestion.reviewed == reviewed)
        items = query.order_by(WritingSuggestion.created_at.desc()).all()
        return [i.to_dict() for i in items]


@app.patch("/api/writing/suggestions/{suggestion_id}/review")
def mark_writing_suggestion_reviewed(suggestion_id: int):
    with get_session() as session:
        item = session.query(WritingSuggestion).filter(WritingSuggestion.id == suggestion_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        item.reviewed = True
        session.commit()
        session.refresh(item)
        return item.to_dict()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
