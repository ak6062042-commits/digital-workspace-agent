import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

# Ensure project root is in sys.path for direct DB fallback
LOCAL_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(LOCAL_AGENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from config import (
        BACKEND_API_URL,
        API_TOKEN,
        POLL_INTERVAL,
        FORCE_HEARTBEAT_INTERVAL,
        DIRECT_DB_FALLBACK,
        CAPTURE_ENABLED,
        LOG_LEVEL,
    )
    from snapshot import capture_snapshot
except ImportError:
    from .config import (
        BACKEND_API_URL,
        API_TOKEN,
        POLL_INTERVAL,
        FORCE_HEARTBEAT_INTERVAL,
        DIRECT_DB_FALLBACK,
        CAPTURE_ENABLED,
        LOG_LEVEL,
    )
    from .snapshot import capture_snapshot

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [LocalAgent] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("LocalAgentWatcher")

WIDGET_WINDOW_MARKER = "digital workspace command center"
WIDGET_PROCESS_NAMES = {"python.exe", "pythonw.exe", "python", "pythonw"}


def is_workspace_widget_snapshot(snapshot: Dict[str, Any]) -> bool:
    """Return true only for this agent's PyQt command-center window.

    We deliberately require both the explicit window title and a Python process
    name, so a normal Word/VS Code document mentioning the product name is not
    excluded from capture.
    """
    app = (snapshot.get("active_app") or "").strip().lower()
    title = (snapshot.get("active_window_title") or "").strip().lower()
    return app in WIDGET_PROCESS_NAMES and WIDGET_WINDOW_MARKER in title


def save_to_database_directly(snapshot: Dict[str, Any]) -> bool:
    """Fallback: write the state snapshot directly to the SQLite database."""
    try:
        from backend.db.db import get_session, init_db
        from backend.db.models import StateSnapshot

        init_db()
        with get_session() as session:
            # Parse captured_at to datetime object if string
            captured_at_val = snapshot.get("captured_at")
            if isinstance(captured_at_val, str):
                try:
                    captured_at_dt = datetime.fromisoformat(captured_at_val.replace("Z", "+00:00"))
                except Exception:
                    captured_at_dt = datetime.utcnow()
            else:
                captured_at_dt = datetime.utcnow()

            snap_record = StateSnapshot(
                active_app=snapshot.get("active_app"),
                active_window_title=snapshot.get("active_window_title"),
                browser_url=snapshot.get("browser_url"),
                browser_tab_title=snapshot.get("browser_tab_title"),
                captured_at=captured_at_dt,
            )
            session.add(snap_record)
            session.commit()
            session.refresh(snap_record)
            logger.info("Saved snapshot directly to SQLite (ID: %s)", snap_record.id)
            return True
    except Exception as e:
        logger.warning("Direct DB fallback failed: %s", e)
        return False


def post_snapshot(snapshot: Dict[str, Any], backend_url: str = BACKEND_API_URL) -> bool:
    """Send state snapshot to the backend API via HTTP POST."""
    if requests is None:
        logger.warning("'requests' library is not installed.")
        if DIRECT_DB_FALLBACK:
            return save_to_database_directly(snapshot)
        return False

    try:
        headers = {"Content-Type": "application/json", "X-Workspace-Token": API_TOKEN}
        if not API_TOKEN:
            logger.error("API_TOKEN is not configured; refusing to send workspace metadata over HTTP.")
            return save_to_database_directly(snapshot) if DIRECT_DB_FALLBACK else False
        response = requests.post(backend_url, json=snapshot, headers=headers, timeout=2.5)
        if response.status_code in (200, 201):
            logger.info("Successfully posted snapshot to backend: %s", response.status_code)
            return True
        else:
            logger.warning("Backend returned HTTP %s: %s", response.status_code, response.text)
    except Exception as exc:
        logger.info("Backend unreachable (%s). Using fallback if enabled.", exc)

    if DIRECT_DB_FALLBACK:
        return save_to_database_directly(snapshot)

    return False


def has_state_changed(curr: Dict[str, Any], prev: Optional[Dict[str, Any]]) -> bool:
    """Check if meaningful user context fields have changed."""
    if prev is None:
        return True

    keys_to_compare = [
        "active_app",
        "active_window_title",
        "browser_url",
        "browser_tab_title",
    ]
    return any(curr.get(k) != prev.get(k) for k in keys_to_compare)


def run_watcher(
    interval: float = POLL_INTERVAL,
    backend_url: str = BACKEND_API_URL,
    once: bool = False,
    dry_run: bool = False,
):
    """Main watcher loop."""
    if not CAPTURE_ENABLED and not dry_run:
        logger.warning("CAPTURE_ENABLED is false. No workspace metadata will be collected. Set it to true only after reviewing the privacy settings.")
        return
    logger.info("Starting Local Agent Watcher...")
    logger.info("Backend URL: %s | Poll Interval: %ss | Dry-run: %s", backend_url, interval, dry_run)

    last_snapshot = None
    last_sent_time = 0.0
    widget_was_foreground = False

    try:
        while True:
            current_time = time.time()
            snapshot = capture_snapshot()

            # The command center is an agent control surface, not user work.
            # Ignore it completely so it cannot overwrite the latest useful
            # state or cause a Python/widget feedback loop.
            if is_workspace_widget_snapshot(snapshot):
                if not widget_was_foreground:
                    logger.info("Workspace widget is foreground; preserving the last real workspace state.")
                widget_was_foreground = True
                if once:
                    logger.info("Run-once flag specified while widget was foreground. No self-snapshot was sent.")
                    break
                time.sleep(interval)
                continue
            widget_was_foreground = False

            changed = has_state_changed(snapshot, last_snapshot)
            heartbeat_due = (current_time - last_sent_time) >= FORCE_HEARTBEAT_INTERVAL

            if changed or heartbeat_due:
                reason = "State changed" if changed else "Heartbeat interval"
                logger.info(
                    "Snapshot triggered (%s) -> App: '%s' | Window: '%s'",
                    reason,
                    snapshot.get("active_app"),
                    snapshot.get("active_window_title"),
                )

                if dry_run:
                    print(json.dumps(snapshot, indent=2))
                else:
                    post_snapshot(snapshot, backend_url)

                last_snapshot = snapshot
                last_sent_time = current_time

            if once:
                logger.info("Run-once flag specified. Exiting watcher.")
                break

            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Watcher interrupted by user. Exiting cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Digital Workspace Local Agent Watcher")
    parser.add_argument("--once", action="store_true", help="Capture and send a single snapshot then exit")
    parser.add_argument("--interval", type=float, default=POLL_INTERVAL, help="Polling interval in seconds")
    parser.add_argument("--backend-url", type=str, default=BACKEND_API_URL, help="Backend API snapshot endpoint")
    parser.add_argument("--dry-run", action="store_true", help="Print snapshot to stdout without sending or saving")
    args = parser.parse_args()

    run_watcher(
        interval=args.interval,
        backend_url=args.backend_url,
        once=args.once,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
