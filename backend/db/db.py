from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base

DATABASE_URL = "sqlite:///./backend/db/app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}, 
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()