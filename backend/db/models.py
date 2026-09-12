import json
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

REOPENABLE_APP_NAMES = {
    "terminal", "cmd.exe", "windowsterminal.exe", "vscode", "code", "code.exe",
    "browser", "chrome", "chrome.exe", "google chrome", "calculator", "calc.exe",
    "notes", "notepad", "notepad.exe", "word", "winword", "winword.exe",
    "files", "explorer", "explorer.exe",
}


def _is_agent_dashboard_url(url: str | None) -> bool:
    parsed = urlparse(url or "")
    try:
        port = parsed.port
    except ValueError:
        return False
    return (parsed.hostname or "").lower() in {"localhost", "127.0.0.1"} and port == 5173


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    done = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_app = Column(String(255), nullable=True)
    source_title = Column(String(500), nullable=True)

    def to_dict(self):
        # A historical task may have been created while the agent dashboard was
        # focused.  It must be relinked, even though "Google Chrome" itself is
        # normally a launchable application.
        dashboard_context = _is_agent_dashboard_url(self.source_url)
        has_context = not dashboard_context and bool(
            (self.source_url or "").startswith(("http://", "https://"))
            or (self.source_app or "").strip().lower() in REOPENABLE_APP_NAMES
        )
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "done": self.done,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "status": "done" if self.done else (self.status or "pending"),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "source_url": self.source_url,
            "source_app": self.source_app,
            "source_title": self.source_title,
            "has_context": has_context,
        }


class StateSnapshot(Base):
    __tablename__ = "state_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    active_app = Column(String(255), nullable=True)
    active_window_title = Column(String(500), nullable=True)
    browser_url = Column(String(1000), nullable=True)
    browser_tab_title = Column(String(500), nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "active_app": self.active_app,
            "active_window_title": self.active_window_title,
            "browser_url": self.browser_url,
            "browser_tab_title": self.browser_tab_title,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
        }


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(255), nullable=True)
    raw_title = Column(String(500), nullable=True)
    raw_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    reviewed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self, include_raw: bool = False):
        payload = {"id": self.id, "source": self.source, "summary": self.summary, "reviewed": self.reviewed, "created_at": self.created_at.isoformat() if self.created_at else None}
        if include_raw:
            payload["raw_title"] = self.raw_title
            payload["raw_content"] = self.raw_content
        return payload


class WritingSuggestion(Base):
    __tablename__ = "writing_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_url = Column(String(1000), nullable=True)
    source_title = Column(String(500), nullable=True)
    excerpt = Column(Text, nullable=True)
    suggestion_text = Column(Text, nullable=True)
    related_links = Column(Text, nullable=True)
    reviewed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        try:
            research = json.loads(self.related_links) if self.related_links else {}
        except (TypeError, ValueError):
            research = {}
        return {
            "id": self.id,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "excerpt": self.excerpt,
            "suggestion_text": self.suggestion_text,
            "keywords": research.get("keywords", []),
            "related_queries": research.get("related_queries", []),
            "reviewed": self.reviewed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
