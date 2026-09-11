# System Agent & Browser Extension (Track C)

This component provides real-time workspace context to the **Digital Workspace Agent** by continuously capturing and synchronizing operating system state (active application, active window title) and browser state (active tab title, URL) into the backend database.

---

## Directory Structure

```
system-agent/
├── local-agent/
│   ├── config.py         # Polling interval, backend URL, and platform detection
│   ├── snapshot.py       # Cross-platform window & browser state extraction
│   ├── watcher.py        # Background polling daemon & change detector
│   └── requirements.txt  # Python dependencies (requests, psutil)
└── browser-extension/
    ├── manifest.json     # Chrome Manifest V3 configuration
    ├── background.js     # Tab change listener & sync service worker
    ├── popup.html        # Status popup UI
    └── popup.js          # Popup controller & manual sync trigger
```

---

## 1. Local Agent Setup & Usage

### Prerequisites
- Python 3.10+
- Installed dependencies:
  ```bash
  pip install -r system-agent/local-agent/requirements.txt
  ```

### Quick Run: Single Snapshot
Capture and inspect the current OS and window state without running a daemon:
```bash
python system-agent/local-agent/snapshot.py
```

Sample output:
```json
{
  "active_app": "Electron",
  "active_window_title": "digital-workspace-agent — Code Editor",
  "browser_url": null,
  "browser_tab_title": null,
  "captured_at": "2026-09-11T05:58:14.865986+00:00",
  "metadata": {
    "os_platform": "darwin",
    "hostname": "macbook-m1",
    "source": "local-agent"
  }
}
```

### Running the Continuous Watcher Daemon
Start the watcher daemon to continuously detect window/app changes and stream them to the backend:
```bash
python system-agent/local-agent/watcher.py
```

#### CLI Options
- `--once`: Capture a single snapshot, submit it, and exit.
- `--dry-run`: Print captured snapshot to stdout without sending to backend or saving.
- `--interval <seconds>`: Set polling interval (default: `3.0` seconds).
- `--backend-url <url>`: Override backend snapshot endpoint (default: `http://localhost:8000/api/snapshot`).

#### Offline & Direct-to-Database Fallback
If the backend HTTP server (`uvicorn backend.main:app`) is not running, the watcher automatically falls back to writing directly into `backend/db/app.db` using SQLAlchemy, ensuring you can test local state tracking immediately.

---

## 2. macOS Permissions (Accessibility & Automation)

On macOS, `snapshot.py` uses native AppleScript (`osascript`) to inspect the frontmost application and active browser tabs (Google Chrome, Safari, Brave, Arc, Edge).

1. **System Events Permission**: On first run, macOS may prompt to allow `osascript` / your terminal or IDE to control "System Events". Click **Allow**.
2. **Browser Automation Permission**: To read active tab URLs from Chrome/Safari, macOS may ask for permission to control that browser. Click **OK**.
3. If permissions were previously denied, verify in:
   `System Settings` → `Privacy & Security` → `Automation` & `Accessibility`.

---

## 3. Browser Extension Setup (Chrome / Brave / Edge / Arc)

The browser extension complements the OS agent by providing real-time tab change updates even when the browser is running across multiple displays or virtual workspaces.

### Installation Steps
1. Open your Chromium-based browser and navigate to `chrome://extensions` (or `brave://extensions`, `edge://extensions`).
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked**.
4. Select the directory:
   `<project_root>/system-agent/browser-extension`
5. The **Digital Workspace Agent — Browser Companion** icon will appear in your extension toolbar.
6. Click the extension icon to view the active tab, connection status to `http://localhost:8000`, and trigger a manual sync.
