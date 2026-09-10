from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    done = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_at = Column(DateTime, nullable=True)  

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "done": self.done,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "due_at": self.due_at.isoformat() if self.due_at else None,
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