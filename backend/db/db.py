from contextlib import contextmanager
from datetime import timedelta
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.db.models import Base, StateSnapshot, Task, _is_agent_dashboard_url

DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 10},
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    # Lightweight forward-only migration for the existing MVP SQLite database.
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(tasks)"))}
        if "status" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'"))
        if "updated_at" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN updated_at DATETIME"))
        if "source_url" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN source_url VARCHAR(1000)"))
        if "source_app" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN source_app VARCHAR(255)"))
        if "source_title" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN source_title VARCHAR(500)"))
    _backfill_task_contexts()


def _backfill_task_contexts() -> None:
    """Best-effort link for pre-context tasks, only when a nearby snapshot exists."""
    with SessionLocal() as session:
        tasks = session.query(Task).filter(Task.source_url.is_(None), Task.source_app.is_(None)).all()
        changed = False
        for task in tasks:
            if not task.created_at:
                continue
            earliest = task.created_at - timedelta(minutes=10)
            snapshot = (
                session.query(StateSnapshot)
                .filter(StateSnapshot.captured_at >= earliest, StateSnapshot.captured_at <= task.created_at + timedelta(minutes=2))
                .order_by(StateSnapshot.captured_at.desc())
                .first()
            )
            is_widget = bool(snapshot) and (
                "python" in (snapshot.active_app or "").lower()
                and "digital workspace command center" in (snapshot.active_window_title or "").lower()
            )
            if snapshot and not _is_agent_dashboard_url(snapshot.browser_url) and not is_widget:
                task.source_url = snapshot.browser_url
                task.source_app = snapshot.active_app
                task.source_title = snapshot.browser_tab_title or snapshot.active_window_title
                changed = True
        if changed:
            session.commit()


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
