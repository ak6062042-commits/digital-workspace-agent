# Digital Workspace Agent

Digital Workspace Agent is a local-first, user-controlled workspace assistant. It combines a FastAPI control plane, a React dashboard, optional desktop-state capture, a Chrome companion, a Microsoft Word task pane, and a small desktop widget. Its purpose is to help a person understand their current work context, organize tasks, obtain writing assistance, and launch narrowly approved actions without silently controlling the computer.

The project is designed around a simple rule: observing context, suggesting work, and taking an action are different trust levels. The system does not capture anything or perform an external action unless the relevant feature has been enabled or directly requested by the user.

## What the project provides

| Area | Capability | How it behaves |
| --- | --- | --- |
| Workspace awareness | Local snapshots of the active app, window title, and optionally the active browser tab | Capture is disabled by default. Snapshot fields are redacted, normalized, deduplicated, capped, and retained only for a configured period. |
| Conversational control | Natural-language chat interface | The backend classifies the request, generates a typed plan, and applies policy before an execution-capable step can run. |
| Human approval | Explicit confirmation for consequential actions | A confirmation card is returned to the client; no hidden approval is inferred. Confirmation requests are intentionally in memory and expire if the backend restarts. |
| Task management | Create, list, update, navigate to, and link tasks to the current workspace | Tasks support pending, ongoing, and done states plus sanitized source context. |
| Research assistance | Live web research with source-linked briefs | With `EXA_API_KEY` configured, a research request uses Exa's live search and inline source text; otherwise it falls back to DuckDuckGo with Bing RSS fallback. It opens a visible desktop search and returns a concise cited brief. |
| Writing support | Summarize, improve, explain, and brainstorm from supplied text | Handles drafts, notes, selected text, and browser pages up to practical working lengths, then returns local analysis plus relevant research queries. |
| Browser companion | Chrome extension for active-tab context, page summaries, and selected-text analysis | Active-tab sync is opt-in. Page/selection content is injected only after a direct popup action. |
| Word integration | Local Microsoft Word task pane | Reads selected document text only after the person presses an analysis button. |
| Notifications | Authenticated local notification inbox | Notifications are summarized, reviewable, deletable, redacted, and subject to retention cleanup; there is no native WhatsApp or OS-notification bridge. |
| Desktop companion | PyQt widget for quick workspace/status access | Uses the same authenticated API and policy layer as the web dashboard. |
| Operations | Local SQLite persistence, indexes, retention, health endpoint, Docker support, tests | SQLite uses WAL mode, foreign keys, a busy timeout, indexes, and rollback-safe sessions. |

## Design principles and non-goals

This is a personal, local-development workspace tool. It is not a covert monitoring system, a remote multi-user automation platform, a general shell executor, or a replacement for an enterprise identity/access-control system.

- User authority comes first. The system can explain, suggest, or prepare a step, but consequential work requires a visible request and confirmation flow.
- Data minimization comes before convenience. The snapshot API accepts a narrow contract rather than arbitrary application metadata.
- Local operation is the default. The API, SQLite database, dashboard, widget, extension, and add-in are intended to run on the same machine during development.
- Tool access is allowlisted. Desktop app launches use named identifiers rather than arbitrary executable paths. Browser navigation accepts only supplied `http` or `https` URLs.
- AI/network features are opt-in. External model access is disabled by default, and default research opens a user-visible browser query instead of fetching pages server-side.
- The project does not record screenshots, keystrokes, clipboard contents, or document contents automatically.

## System flow

```text
Optional local context sources
  ├─ System watcher (app/window metadata; disabled by default)
  ├─ Chrome companion (active tab after opt-in)
  └─ Word task pane (selection after button click)
                    │
                    ▼
           FastAPI control plane
  validation → redaction → SQLite persistence → state estimator
                    │
                    ▼
        planner → policy → confirmation → executor
                    │
                    ▼
      approved local tools or user-visible browser action
                    │
                    ▼
 React dashboard / PyQt widget / Chrome popup / Word task pane
```

The planner assigns work to one of four levels:

| Level | Typical examples | Result |
| --- | --- | --- |
| Observe | Show current state, list tasks, view recent items | Read-only response. |
| Assist | Create a task or prepare a safe, allowlisted action | Structured result or an approved action request. |
| Hybrid | Research a topic | Opens a visible browser search when the user asks. |
| Consequential | Anything that changes an external application or requires a protected action | Returns a confirmation request before execution. |

Unknown or malformed natural-language commands do not create side effects.

## Repository layout

```text
backend/                 FastAPI app, policy, planner, agents, database models
frontend/                React + Vite dashboard
system-agent/local-agent/ Optional local active-window watcher
system-agent/floating-widget/ Optional PyQt desktop widget
system-agent/browser-extension/ Manifest V3 Chrome companion
system-agent/word-addin/ Microsoft Word task-pane files
scripts/                 Setup, launch, test, and configuration helpers
tests/                   Backend/unit security and behavior coverage
docs/                    Architecture, API contracts, remediation and quality plans
docker-compose.yaml      Local container development stack
.env.example             Safe-by-default configuration template
```

## Feature guide

### 1. Local backend and control plane

The FastAPI application is the trusted boundary between every client and local tools. It:

- Loads configuration from `.env` and fails startup when a required API token is missing or too short.
- Requires the `X-Workspace-Token` header for every `/api/*` endpoint. Only `/health` is public for local readiness checks.
- Applies request-size limits and a per-client/user-agent rate limit before API work is performed.
- Uses an explicit trusted-host allowlist and explicit CORS origins. Wildcard CORS is not used.
- Rejects unexpected fields in sensitive request models instead of silently accepting arbitrary metadata.
- Redacts sensitive strings before storage or response serialization and sanitizes workspace URLs.
- Starts retention cleanup for snapshots, notifications, and writing records, then serves the dashboard and API.

The public settings endpoint exposes safe operational facts for clients, such as whether capture and external LLM usage are enabled. It does not return secrets.

### 2. Workspace snapshots and context timeline

A snapshot is deliberately small. The accepted fields are the active application name, active window title, browser URL, browser tab title, and capture timestamp.

- Snapshot titles and URLs are redacted before storage and before they are sent back to clients.
- URL sanitization removes embedded user information, fragments, and common sensitive query parameters such as tokens, authorization data, passwords, signatures, sessions, and codes.
- Repeated equivalent snapshots within the configured deduplication window are treated as duplicates.
- Overview and history responses enforce configured limits and report counts, preventing an unbounded dashboard payload.
- The dashboard can show the latest context, a bounded overview, history, and a diff between captured states.
- Snapshot history can be deleted through its authenticated API route.

The system watcher is optional and starts with `CAPTURE_ENABLED=false`. When enabled, it reads active-window metadata on Windows, macOS, or Linux X11. It filters out its own widget window. Browser URL capture needs the Chrome companion on Windows; on macOS it requires Automation permission. Linux support requires an X11 environment with `xdotool`; Wayland is not supported by the current watcher implementation.

### 3. Dashboard experience

The React/Vite dashboard is the primary daily interface. It includes:

- Authenticated chat with structured plan/result cards.
- A workspace panel for current context, sync status, manual refresh, state diffs, and bounded recent history.
- A task board with filtering, task creation, status updates, navigation, and current-context linking.
- A writing panel for pasted text and explicit writing operations.
- Planner suggestion viewing, dismissal, and user-triggered research.
- A notification inbox with review controls and a deletion confirmation step.
- Optional voice input and voice output controls. Speech recognition only prepares text for the normal Send action; it never auto-sends or auto-executes a command.
- Sanitized Markdown rendering for assistant messages.
- A multiline command composer, clear-chat control, dedicated quick-research input, completed-task filtering, action-feedback toasts, and visible API errors.
- A responsive workspace drawer for narrower screens, a client request timeout, and non-overlapping polling so a slow refresh cannot stack repeated dashboard requests.

The dashboard polls workspace overview data at a configurable interval, while preserving manual refresh for a person who wants an immediate update.

### 4. Chat, planning, policy, and execution

The chat route accepts a user request, current context, and optional request metadata. It passes the request through the following layers:

1. **State estimator**: builds a bounded current-workspace view from safe snapshot and task data.
2. **Planner**: maps supported intents to a typed execution plan. Supported categories include inspecting context, listing or creating tasks, completing a task, launching an allowlisted app, opening a supplied link, research, and help.
3. **Policy engine**: determines whether the step is observational, directly permitted, or requires confirmation.
4. **Executor**: calls only registered tools/agents after policy permits the step.

The backend never treats arbitrary prose as a shell command. There is no generic remote-command endpoint, and app launching is restricted to the identifiers below:

| Identifier | Intended application |
| --- | --- |
| `terminal` | Platform terminal application |
| `vscode` | Visual Studio Code, when installed |
| `browser` | Default/browser launcher |
| `calculator` | Platform calculator |
| `notes` | Platform notes application where available |
| `word` | Microsoft Word where available |
| `files` | Platform file manager |

Platform availability varies. An unavailable application returns a controlled error rather than falling back to arbitrary paths or commands.

The chat path sends plans through policy and returns confirmation requests when the plan requires one. The dedicated local tool routes (`/api/os/app`, `/api/os/terminal`, and `/api/browser/open`) directly perform their narrow allowlisted action once an authenticated client invokes them. The API token is therefore an authority credential: keep it private and do not expose the backend beyond its trusted local boundary.

### 5. Tasks and context linking

Tasks provide a lightweight work queue that can be connected to the workspace timeline.

- Create tasks with a title and optional source context.
- List current tasks and use pending, ongoing, or done status.
- Patch a task status as work progresses.
- Link a task to the latest sanitized workspace context.
- Ask the backend to navigate to a task's stored source URL when one is present and valid.
- Ask conversationally to list, create, or complete supported tasks.

Task records use forward-compatible database migration handling and sanitized URL/title context. Source context is not a backdoor to arbitrary desktop execution.

### 6. Research and browser assistance

Research is deliberately user-visible and user-triggered.

- The default provider is `exa`. Add `EXA_API_KEY` to `.env` to use Exa's live search and inline extracted text for source-attributed briefs. If the key is blank, invalid, or the Exa request fails, research automatically continues with DuckDuckGo and its Bing RSS fallback.
- The dashboard keeps both the visible desktop search and clickable source cards, so you can continue reading any source in the browser.
- Source cards show the title, domain, and extractive snippet before opening. Retrieved pages are treated as untrusted; automated retrieval rejects credential-bearing, local, private, and redirect-to-private targets.
- Set `WEB_SEARCH_PROVIDER=chrome` when you specifically want browser-only manual research with no retrieval or summary in the assistant.
- Opening a link requires an explicitly supplied `http` or `https` URL.
- The Chrome popup can request a summary of the active tab only after the user presses **Summarize Tab**.
- The popup can analyze selected text only after the user presses its analysis action.
- The Chrome companion can submit up to 18,000 characters from an explicitly requested page summary and up to 12,000 selected characters for a writing pass.
- Browser summaries use extractive ranking, return key takeaways and keywords, and can process up to 20,000 submitted characters.

Non-default research-provider paths are available for development use, but they make outbound requests and should be enabled only after reviewing the privacy implications for your environment.

### 7. Writing assistance

Writing analysis is a consent-based API and dashboard workflow. A person supplies text, chooses an operation, and explicitly provides `consent=true`.

Supported operations are:

| Operation | Purpose |
| --- | --- |
| `summarize` | Produce a concise local summary of supplied text. |
| `improve` | Offer local wording and readability improvements. |
| `explain` | Explain the supplied content in plainer terms. |
| `ideas` | Generate focused follow-up ideas from supplied content. |

Input is size-bounded, redacted, and stored only as a minimized record needed for the suggestion workflow. Results include a local suggestion, keywords, and optional related research queries. The service does not silently read open documents, browser pages, or the clipboard.

### 8. Chrome companion

The `system-agent/browser-extension` directory contains a Manifest V3 companion extension for local development.

- It uses `activeTab`, `tabs`, `storage`, and `scripting` permissions, with host access limited to the local backend addresses.
- It has no always-running content script.
- The user stores the local API token in extension storage.
- **Sync active tab** is an opt-in action; after it is enabled, only active tab/app metadata, title, and URL are sent to the snapshot endpoint.
- **Summarize Tab** and selected-text analysis inject code into the active tab only following a direct popup interaction.
- Captured URL/title data still passes through backend redaction and URL sanitization.

Load it from Chrome's `chrome://extensions` page using **Developer mode** → **Load unpacked**, then select the `system-agent/browser-extension` folder. Use the popup to configure the backend URL and API token.

### 9. Microsoft Word add-in

The `system-agent/word-addin` directory contains a local task pane served by the backend at `/word-addin`.

- The task pane asks for the API token and calls the local writing API.
- It requests the current Word selection with Office.js only after the person chooses the analysis action.
- It presents the resulting local writing assistance in the pane.
- It does not monitor the document or upload its contents automatically.

The supplied manifest is intended for local HTTP development. Word may display a development warning. Deployments involving Word on the web or managed organizations normally require HTTPS and manifest URL changes appropriate to the organization.

### 10. Desktop widget

The optional PyQt widget is a resizable personal command center that reads workspace overview and uses the same chat API.

- Separates daily work into **Today**, **Research**, and **Inbox & Writing** tabs, with a current-work summary and connection feedback.
- Supports quick commands, current-context research, task completion, task context linking/reopening, review actions, planner dismissal, writing-related research, and explicit source buttons.
- Shows source domains and requires a user click before opening an external source page.
- Requires the separate widget dependencies and a running backend.

### 11. Notifications

Notifications are an authenticated, local inbox abstraction.

- Ingest a notification through the API.
- Read a bounded notification list.
- Mark notification records reviewed.
- Delete notification records.
- Apply redaction, minimized listing output, and retention cleanup.

There is intentionally no direct integration with native desktop notifications, messaging platforms, or WhatsApp in this repository. An integration should be added only with its own consent, credential, data-minimization, and policy design.

## Privacy and data handling

| Data category | When it is read | Stored form | Important safeguards |
| --- | --- | --- | --- |
| Active app/window metadata | Only when the local watcher is enabled | Sanitized snapshot | Capture defaults off; self-widget filtering; retention and deduplication. |
| Browser URL and title | Chrome opt-in sync or supported platform capture | Sanitized snapshot | No browser content capture for snapshots; credentials/fragments/sensitive parameters removed. |
| Browser page text/selection | Only after a Chrome popup command | Bounded local analysis/suggestion record | No persistent content-script collection; direct user interaction is required. |
| Word selection | Only after a Word task-pane action | Bounded writing suggestion record | Office.js selection call is button-triggered. |
| Writing text | Only after a consented writing request | Redacted/minimized writing record | Input size limit, retention cleanup, no automatic document reading. |
| Task data | User or planner task action | SQLite task record | Status and source context are validated/sanitized. |
| Notification payload | Authenticated ingestion | Redacted/minimized notification record | Review/delete endpoints and retention cleanup. |
| API token | Client authentication | Configuration/client local storage where configured | Never exposed through the settings response or logged deliberately. |

Redaction covers common secret-bearing field names and patterns, including passwords, API keys, tokens, authorization values, private keys, e-mail-like values, and payment-card-like values. It is a protective control, not a guarantee that every possible sensitive string in a title is detectable. Keep capture disabled when the metadata itself would be inappropriate to retain.

## Quick start

### Prerequisites

- Python 3.11 or later
- Node.js 20 or later with npm
- Windows is the most complete local-watcher target; the backend and dashboard are cross-platform where their dependencies are available

### Windows setup

From the repository root:

```bat
scripts\setup.bat
```

The setup script creates or repairs `.env`, generates a private API token without printing it, mirrors that token to `VITE_API_TOKEN`, installs dependencies, and initializes the schema. Review `.env` before starting anything, and leave `CAPTURE_ENABLED=false` until you intentionally want active-window collection.

Start the backend in one terminal:

```bat
scripts\run_backend.bat
```

Start the dashboard in a second terminal:

```bat
scripts\run_frontend.bat
```

Then open `http://localhost:5173`. The backend health check is at `http://127.0.0.1:8000/health`.

### macOS or Linux setup

The POSIX helper performs the equivalent setup:

```bash
./scripts/setup.sh
```

It creates `.venv`, creates or validates local configuration, installs backend/watcher/widget requirements, initializes the SQLite schema, and installs frontend packages when npm is available. Then start the services in separate terminals:

```bash
./scripts/run_backend.sh
./scripts/run_frontend.sh
```

To perform the setup manually, install `backend/requirements.txt`, `system-agent/local-agent/requirements.txt`, and `system-agent/floating-widget/requirements.txt`; initialize the database with `from backend.db.db import init_db; init_db()`; then run `npm install` in `frontend`.

## Daily operation

1. Start the backend and confirm `/health` returns an OK response.
2. Start the dashboard and use its configured token to access local APIs.
3. Use chat, tasks, workspace view, notifications, and writing help without enabling capture.
4. If you want active-window context, set `CAPTURE_ENABLED=true`, restart the backend if needed, and run the optional watcher with its configured token.
5. If you want accurate active Chrome-tab context on Windows, load and configure the Chrome companion, then choose its opt-in sync control.
6. If you want Word selection analysis, load the local add-in and use its task-pane action.
7. Review any confirmation card before allowing a consequential action to proceed.

## Optional client setup

### Local state watcher

After reviewing the privacy implications, set `CAPTURE_ENABLED=true` in `.env`, start the backend, and run this from the activated environment:

```powershell
.venv\Scripts\python system-agent\local-agent\watcher.py
```

On macOS or Linux, activate `.venv` first and use `python system-agent/local-agent/watcher.py`. The watcher sends snapshots only through the authenticated API; if the backend is unavailable, it drops the snapshot and logs the failure instead of writing directly to SQLite.

### Chrome companion

1. Open `chrome://extensions`, enable **Developer mode**, and load unpacked `system-agent/browser-extension`.
2. Open the extension popup and enter the `API_TOKEN` value from `.env`.
3. Enable active-tab sync only if you want active app/tab title/URL stored as local workspace context.
4. Use **Summarize Tab** or selected-text analysis only for the active page and content you intend to submit.

After modifying extension files, use **Reload** on its `chrome://extensions` card. A task created before its intended context was captured cannot be reconstructed automatically: focus the relevant app or tab, wait for a snapshot, then use **Link current app/tab** on the task.

### Word writing assistant

1. Start the backend.
2. In Word for Windows, open **Home → Add-ins → More Add-ins → My Add-ins → Upload My Add-in**.
3. Upload [manifest.xml](system-agent/word-addin/manifest.xml) and open the Workspace Writing Assistant task pane.
4. Enter the local `API_TOKEN` once in the task pane.
5. Select text and choose **Analyze selected text**.

After a code update, close/reopen the task pane or remove/re-add the development add-in so Word is not using a cached page. The selection is sent to the local API, not to Chrome; selecting a related query only opens that chosen query in Chrome.

### Floating widget

With the backend running, start the optional PyQt widget:

```powershell
.venv\Scripts\python system-agent\floating-widget\widget.py
```

It is a client of the same authenticated API and does not create independent automation rules.

## Configuration

Copy `.env.example` to `.env`; do not commit the resulting file. The template contains the full set of supported variables. The most important settings are below.

| Variable | Default | Purpose |
| --- | --- | --- |
| `BACKEND_HOST` | `127.0.0.1` | Network interface for direct local development. Keep loopback unless deliberately deploying behind a protected boundary. |
| `BACKEND_PORT` | `8000` | Backend port. |
| `DATABASE_URL` | `sqlite:///./backend/db/app.db` | SQLite database URL. |
| `API_TOKEN` | placeholder | Required API token passed as `X-Workspace-Token`; use a long random secret. |
| `VITE_API_TOKEN` | placeholder | Token compiled into the local dashboard development configuration; must match the backend token. |
| `CORS_ORIGIN` | local Vite origins | Comma-separated explicit browser origins permitted to call the API. |
| `ALLOWED_HOSTS` | local hosts/test host | Trusted Host allowlist. |
| `REQUEST_MAX_BYTES` | `262144` | Maximum accepted request body size, sized for long page and document analysis. |
| `RATE_LIMIT_PER_MINUTE` | `600` | Per client/user-agent request ceiling. |
| `SNAPSHOT_RETENTION_DAYS` | `14` | Snapshot retention period. |
| `CONTENT_RETENTION_DAYS` | `30` | Writing and notification retention period. |
| `OVERVIEW_ITEMS_LIMIT` | `50` | Maximum dashboard overview records; server caps this at 100. |
| `SNAPSHOT_DEDUP_SECONDS` | `5` | Equivalent-state deduplication window. |
| `AGENT_POLL_INTERVAL` | `3.0` | Optional watcher capture cadence. |
| `AGENT_HEARTBEAT_INTERVAL` | `30.0` | Optional watcher heartbeat cadence. |
| `CAPTURE_ENABLED` | `false` | Enables optional active-window metadata capture. |
| `DIRECT_DB_FALLBACK` | `false` | Kept for configuration compatibility; direct watcher-to-database fallback is not used. |
| `AUTO_EXECUTE_LOW_RISK` | `false` | Controls whether policy may directly execute only the narrowly defined low-risk work. |
| `ALLOW_EXTERNAL_LLM` | `false` | Gate for external model-provider use. |
| `LLM_PROVIDER` | `none` | Configured external provider, if explicitly enabled. |
| `LLM_MODEL` | blank | Model identifier for an explicitly enabled provider. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` | blank | Optional provider credentials; leave blank for local-only operation. |
| `EXA_API_KEY` | blank | API key from Exa. It is used only by the backend and never returned by the settings endpoint. |
| `WEB_SEARCH_PROVIDER` | `exa` | Live web research default. Exa automatically falls back to DuckDuckGo if unavailable. Set `chrome`, `browser`, or `manual` to keep research browser-only. |
| `RESEARCH_MAX_RESULTS` | `6` | Maximum live search results collected for one research request. |
| `RESEARCH_FETCH_RESULTS` | `4` | Number of leading result pages read for a research brief. |
| `RESEARCH_MAX_CHARS` | `6000` | Maximum extracted text read from each result page. |
| `PLANNER_CONTEXT_LIMIT` | `100` | Maximum context records provided to the planner. |
| `PLANNER_SUGGESTION_LIMIT` | `50` | Maximum planner suggestions returned/stored in a bounded cycle. |
| `SUGGESTION_POLL_SECONDS` | `5` | Dashboard/planner suggestion polling cadence. |
| `DOCUMENT_SUGGESTION_SECONDS` | `20` | Minimum document-suggestion timing control. |
| `DOCUMENT_SUGGESTION_COOLDOWN_SECONDS` | `120` | Cooldown between document-related suggestions. |
| `LOG_LEVEL` | `INFO` | Backend logging level. |

### Environment safety notes

- Do not use `*` in `CORS_ORIGIN`.
- Do not bind the backend to a network interface until you have changed the token, host allowlist, origins, and deployment protections for that environment.
- Do not set provider credentials unless you deliberately intend the privacy and network behavior that provider enables.
- Docker exposes both development services on loopback by default, which keeps them local to the host.

## API reference

All `/api/*` routes require:

```http
X-Workspace-Token: <API_TOKEN>
```

`GET /health` is the unauthenticated local health endpoint. See [API contracts](docs/api-contracts.md) for request and response structures.

| Area | Method and path | Function |
| --- | --- | --- |
| Chat | `POST /api/chat` | Classify a user request, plan it, apply policy, and return a response, result, or confirmation request. |
| Confirmations | `POST /api/actions/{confirmation_id}/confirm` | Approve or reject an in-memory pending action. |
| Snapshots | `POST /api/snapshot` | Validate, redact, sanitize, and persist a narrow workspace snapshot. |
| Snapshots | `GET /api/snapshot/latest` | Return the latest sanitized workspace snapshot. |
| Snapshots | `GET /api/workspace/overview` | Return bounded snapshot/task/notification/suggestion overview data and counts. |
| Snapshots | `GET /api/snapshot/diff` | Compare available snapshot states. |
| Snapshots | `GET /api/snapshot/history` | Return bounded sanitized snapshot history. |
| Snapshots | `DELETE /api/snapshot/history` | Remove stored snapshot history. |
| Tasks | `GET /api/tasks` | List tasks. |
| Tasks | `POST /api/tasks` | Create a validated task. |
| Tasks | `PATCH /api/tasks/{id}` | Update a task, including status. |
| Tasks | `POST /api/tasks/{id}/navigate` | Open a valid stored task source URL. |
| Tasks | `POST /api/tasks/{id}/link-current-context` | Attach current sanitized workspace context to a task. |
| Tools | `GET /api/apps` | List known allowlisted desktop applications. |
| Tools | `POST /api/os/app` | Request an allowlisted app launch. |
| Tools | `POST /api/os/terminal` | Open the allowlisted terminal only; it accepts no shell command input. |
| Tools | `POST /api/browser/open` | Open a supplied valid `http` or `https` URL. |
| Tools | `POST /api/browser/summarize` | Produce a local summary from user-provided page text with consent. |
| Writing | `POST /api/writing/analyze` | Analyze consented supplied text using a selected writing operation. |
| Writing | `GET /api/writing/suggestions` | List writing suggestions. |
| Writing | `PATCH /api/writing/suggestions/{id}/review` | Mark a writing suggestion reviewed. |
| Writing | `DELETE /api/writing/suggestions/{id}` | Delete a writing suggestion. |
| Notifications | `POST /api/notifications` | Ingest an authenticated notification record. |
| Notifications | `GET /api/notifications` | List bounded minimized notification records. |
| Notifications | `PATCH /api/notifications/{id}/review` | Mark a notification reviewed. |
| Notifications | `DELETE /api/notifications/{id}` | Delete a notification. |
| Planner | `GET /api/planner/status` | Show planner state/status. |
| Planner | `GET /api/planner/suggestions` | List bounded planner suggestions. |
| Planner | `POST /api/planner/suggestions/{id}/dismiss` | Dismiss a suggestion. |
| Settings | `GET /api/settings` | Return safe client-facing configuration state. |
| Add-in assets | `GET /word-addin/...` | Serve local Word task-pane files. |

The API validates models strictly. Clients should send only documented fields and should handle HTTP errors as controlled responses rather than assuming a request has run.

## Data model and reliability behavior

The local SQLite database holds snapshots, tasks, notifications, and writing suggestions. Database behavior includes:

- WAL journaling for better local read/write behavior.
- A busy timeout and foreign-key enforcement.
- Indexes for the common overview/history/task lookup paths.
- Rollback on failed session work so one database error does not poison later requests.
- Startup retention cleanup using the configured snapshot/content retention periods.
- A forward migration path for task fields used by the current app version.

Planner and dashboard payloads are bounded using dedicated limits. This protects responsiveness and keeps old historical content from becoming an ever-growing prompt or frontend response.

## Docker development

The local Docker Compose setup starts a backend and frontend service:

```powershell
python scripts/bootstrap_config.py
docker compose up --build
```

The backend container listens internally on `0.0.0.0` so the frontend container can reach it, while the host mappings use loopback addresses:

- Dashboard: `127.0.0.1:5173`
- Backend: `127.0.0.1:8000`

Review `.env` before running Compose, especially the API token, CORS origins, capture setting, and any external provider configuration.

## Testing and quality checks

Run the backend suite from the repository root:

```bat
scripts\test.bat
```

Or, with the environment activated:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall backend system-agent widget
Set-Location frontend
npm run build
```

The test suite covers research parsing/synthesis, authentication, configuration validation, URL sanitization/redaction, snapshot constraints, policy behavior, and related backend functions. Run the frontend build after changing React code to catch Vite bundling errors.

## Known limits

- The system is designed for one trusted local user, not an internet-exposed or multi-tenant service.
- Pending confirmation IDs are stored in memory, so backend restarts invalidate them.
- The active-window watcher supports Windows, macOS, and Linux X11 only; it does not support Wayland.
- Browser URLs on Windows depend on the opt-in Chrome companion for reliable capture.
- The repository has no native messaging, WhatsApp, Slack, email, or desktop-notification ingestion adapter.
- Local HTTP Word add-in setup is for development. Managed or web Word scenarios generally need HTTPS and organization-specific deployment configuration.
- Redaction reduces sensitive data exposure but cannot determine the sensitivity of every possible app/window title.
- This project should remain loopback-bound during development unless its deployment and authorization model are deliberately redesigned.

## Further documentation

- [Architecture](docs/architecture.md) explains the layers, trust boundaries, and component relationships.
- [API contracts](docs/api-contracts.md) contains endpoint-level request and response details.
- [Quality improvement plan](docs/quality-improvement-plan.md) records the performance, reliability, privacy, and UX hardening work.
- [Security remediation plan](docs/remediation-plan.md) records the security priorities and completed direction of travel.
- [Configuration template](.env.example) is the authoritative list of runtime environment variables.

## Contribution and maintenance guidance

When extending the project, preserve the control boundary:

1. Add a strict request/response schema before adding a client feature.
2. Redact and minimize sensitive metadata before persistence and API output.
3. Keep new side-effecting tools allowlisted and behind the policy/confirmation workflow.
4. Prefer direct user controls over background collection or automatic execution.
5. Add focused tests for validation, authorization, privacy, error handling, and retention behavior.
6. Update this README and the API/architecture documents when behavior changes.

That discipline keeps the assistant useful without turning a workspace aid into an opaque controller of the user's computer.
