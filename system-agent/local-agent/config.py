import os
import sys
from pathlib import Path

# Base Paths
LOCAL_AGENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LOCAL_AGENT_DIR.parent.parent
DB_FILE_PATH = PROJECT_ROOT / "backend" / "db" / "app.db"

# Server Configuration
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/snapshot")
LATEST_SNAPSHOT_URL = os.getenv("LATEST_SNAPSHOT_URL", "http://localhost:8000/api/snapshot/latest")

# Watcher Configuration
POLL_INTERVAL = float(os.getenv("AGENT_POLL_INTERVAL", "3.0"))  # Seconds between checks
FORCE_HEARTBEAT_INTERVAL = float(os.getenv("AGENT_HEARTBEAT_INTERVAL", "30.0"))  # Send even if unchanged
DIRECT_DB_FALLBACK = os.getenv("DIRECT_DB_FALLBACK", "true").lower() in ("true", "1", "yes")

# OS Platform Identification
OS_PLATFORM = sys.platform  # 'darwin', 'win32', 'linux'
HOSTNAME = os.uname().nodename if hasattr(os, "uname") else os.getenv("COMPUTERNAME", "localhost")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
