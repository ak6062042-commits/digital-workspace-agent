# Digital Workspace Agent

A privacy-conscious, local workspace assistant. It observes permitted workspace metadata, builds a deterministic plan, validates that plan against a safety policy, and executes only approved tools.

```
State estimator -> Planner -> Policy validation -> Executor -> Approved tools
```

The project is designed to assist with workspace context, tasks, research, explicitly submitted writing, and notification organisation. It is not an unrestricted computer-control agent.

## What is implemented

- Workspace state snapshots, history, retention, and context diffs.
- Deterministic State -> Plan -> Validate -> Execute orchestration.
- Task management with `pending`, `ongoing`, and user-confirmed `done` states.
- Controlled web research and safe HTTP(S) browser opening.
- Strict desktop-app allowlist: Terminal, VS Code, Browser, Calculator, Notes, and Files.
- Notification inbox with review and delete controls.
- Explicit writing analysis (summarize, improve, explain, ideas) with local redaction.
- A unified React dashboard, Chrome companion, and floating desktop widget.
- Local API token authentication, strict CORS, request bounds, SQLite WAL/busy timeout, retention cleanup, and tests.

## Privacy and safety defaults

- The backend is loopback-only by default (`127.0.0.1`).
- Every `/api/*` endpoint requires `X-Workspace-Token`.
- The browser extension has **no content script** and never records typing. It can summarize a page or analyze selected text only after a click.
- Local state collection is disabled until `CAPTURE_ENABLED=true` is set.
- The planner never auto-creates tasks or performs background web research. It proposes assistance instead.
- The app launcher never passes user input to a shell and rejects unknown applications.
- Browser/LLM content processing requires explicit consent; external LLM processing is disabled by default.

## Quick start

Prerequisites: Python 3.11+, Node 20+, and npm.

```powershell
scripts\setup.bat
scripts\run_backend.bat
scripts\run_frontend.bat
```

On macOS/Linux:

```bash
./scripts/setup.sh
./scripts/run_backend.sh
./scripts/run_frontend.sh
```

The setup script creates or repairs `.env`, generates a private API token without printing it, installs pinned dependencies, and initializes the schema. Restart Vite after setup so `VITE_API_TOKEN` is loaded.

Open `http://localhost:5173`. To start ambient state metadata collection, first review `.env` and set `CAPTURE_ENABLED=true`, then run:

```powershell
.venv\Scripts\python system-agent\local-agent\watcher.py
```

## Chrome companion

1. Open `chrome://extensions`, enable Developer mode, and load `system-agent/browser-extension`.
2. Open the extension popup and paste the value of `API_TOKEN` from your local `.env`.
3. Optional: enable active-tab metadata sync. It sends only active app/tab title/URL to the local backend.
4. Use **Summarize Tab** or **Analyze selected text** for an explicit one-time analysis.

The extension does not collect keystrokes, form input, page text, or browser metadata by default.

## Configuration

Copying `.env.example` is unnecessary; `scripts/setup.*` maintains `.env`. Important settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKEND_HOST` | `127.0.0.1` | Backend bind address. Non-loopback is rejected outside the Docker container. |
| `BACKEND_PORT` | `8000` | Local backend port. |
| `DATABASE_URL` | SQLite app DB | SQLAlchemy database URL. |
| `API_TOKEN` | generated | Required local API token. |
| `VITE_API_TOKEN` | same token | Dashboard token, consumed at Vite startup. |
| `CORS_ORIGIN` | `http://localhost:5173` | Comma-separated allowed browser origins. |
| `CAPTURE_ENABLED` | `false` | Enables the local state watcher only after explicit opt-in. |
| `SNAPSHOT_RETENTION_DAYS` | `14` | Snapshot retention. |
| `CONTENT_RETENTION_DAYS` | `30` | Notification/writing retention. |
| `ALLOW_EXTERNAL_LLM` | `false` | Reserved explicit opt-in for future external LLM processing. |

## Running with Docker

```bash
docker compose up --build
```

Docker publishes both services only to `127.0.0.1`. The frontend proxies API requests to the backend container and receives the generated token through its development environment.

## Tests and verification

```powershell
scripts\test.bat
cd frontend; npm run build
```

The standard test suite covers planning safety and redaction/allowlisting. Add integration tests for every new tool before granting it executor access.

## Architecture and API

- [Architecture](docs/architecture.md)
- [API contracts](docs/api-contracts.md)
- [System agent and extension](system-agent/README.md)
- [Demo and manual verification](docs/demo-script.md)

## Known limits

- Windows provides app/window metadata; active browser URL capture comes from the explicit browser extension.
- Linux state capture requires X11 and `xdotool`; Wayland support is not yet implemented.
- Notification ingestion is an authenticated API capability. Native WhatsApp/system-notification adapters are intentionally not bundled yet because each needs a consented, platform-specific integration.
- All persistence is local SQLite. Back up or delete the database using your normal OS controls; the API provides deletion endpoints for workspace history, notifications, and writing suggestions.
