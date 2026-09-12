from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.db.models import Base

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


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
