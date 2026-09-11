#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta, timezone

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.db.db import init_db, get_session
from backend.db.models import Task, StateSnapshot


def seed():
    print("Initializing database...")
    init_db()

    with get_session() as session:
        # Check existing count
        existing_tasks = session.query(Task).count()
        existing_snapshots = session.query(StateSnapshot).count()

        if existing_tasks > 0 and existing_snapshots > 0:
            print(f"Database already contains {existing_tasks} tasks and {existing_snapshots} snapshots.")
            print("Adding fresh demo items...")

        now = datetime.now(timezone.utc)

        tasks = [
            Task(
                title="Review Q3 System Integration Architecture",
                description="Finalize integration contract between Coordinator (Track A) and System Agent (Track C).",
                done=False,
                created_at=now - timedelta(hours=3),
                due_at=now + timedelta(days=2),
            ),
            Task(
                title="Configure Chrome Extension Manifest V3",
                description="Add activeTab and host permissions for http://localhost:8000.",
                done=True,
                created_at=now - timedelta(days=1),
                due_at=None,
            ),
            Task(
                title="Benchmark Coordinator Routing Latency",
                description="Test router response times across task_agent and state_agent.",
                done=False,
                created_at=now - timedelta(hours=5),
                due_at=now + timedelta(days=1),
            ),
            Task(
                title="Set up Docker Compose Environment",
                description="Verify containerized backend and frontend run with live code reload.",
                done=True,
                created_at=now - timedelta(days=2),
                due_at=None,
            ),
        ]

        snapshots = [
            StateSnapshot(
                active_app="Visual Studio Code",
                active_window_title="digital-workspace-agent — router.py",
                browser_url=None,
                browser_tab_title=None,
                captured_at=now - timedelta(minutes=25),
            ),
            StateSnapshot(
                active_app="Google Chrome",
                active_window_title="FastAPI Documentation — Overview",
                browser_url="https://fastapi.tiangolo.com/tutorial/",
                browser_tab_title="FastAPI Tutorial - User Guide",
                captured_at=now - timedelta(minutes=10),
            ),
            StateSnapshot(
                active_app="Google Chrome",
                active_window_title="GitHub — ak6062042-commits/digital-workspace-agent",
                browser_url="https://github.com/ak6062042-commits/digital-workspace-agent",
                browser_tab_title="GitHub - digital-workspace-agent",
                captured_at=now - timedelta(seconds=30),
            ),
        ]

        session.add_all(tasks)
        session.add_all(snapshots)
        session.commit()

        print(f"Successfully seeded {len(tasks)} tasks and {len(snapshots)} state snapshots!")


if __name__ == "__main__":
    seed()
