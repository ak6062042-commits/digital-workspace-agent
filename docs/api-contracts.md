# API contracts

Base URL: `http://127.0.0.1:8000`.

All `/api/*` requests require:

```http
X-Workspace-Token: <API_TOKEN>
Content-Type: application/json
```

The health endpoint is intentionally the only unauthenticated endpoint.

## System and state

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Local service health only. |
| `POST` | `/api/snapshot` | Ingest bounded, structured metadata from an opted-in watcher/extension. |
| `GET` | `/api/snapshot/latest` | Latest retained snapshot. |
| `GET` | `/api/workspace/overview` | Bounded combined state for dashboard/widget refreshes. |
| `GET` | `/api/snapshot/diff?limit=5` | Recent workspace changes. |
| `GET` | `/api/snapshot/history?limit=20` | Retained snapshot history. |
| `DELETE` | `/api/snapshot/history` | Delete all state history. |

`POST /api/snapshot` accepts `active_app`, `active_window_title`, `browser_url`, `browser_tab_title`, and optional `captured_at`. Each field is length bounded and raw screenshots are not accepted.

## Planner and executor

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/chat` | Builds and executes/proposes an execution plan. |
| `POST` | `/api/actions/{id}/confirm` | Approves or rejects a pending consequential action. |
| `GET` | `/api/planner/status` | Background planner status. |
| `GET` | `/api/planner/suggestions` | Non-interrupting task/research proposals. |
| `POST` | `/api/planner/suggestions/{id}/dismiss` | Dismiss a proposal. |

Chat response shape includes a human response, `plan`, execution `status`, optional `confirmation_id`, task updates, browser action data, and current state. A plan contains `intent`, `category`, `action`, `arguments`, `confirmation_required`, and `expected_result`.

## Tasks

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/tasks?done=false&task_status=pending` | List tasks. |
| `POST` | `/api/tasks` | Create a task. |
| `PATCH` | `/api/tasks/{id}` | Update title/description/due date or `pending`/`ongoing`/`done`. |
| `POST` | `/api/tasks/{id}/navigate` | Reopen the HTTP(S) tab or approved desktop app captured when the task was created. |
| `POST` | `/api/tasks/{id}/link-current-context` | Explicitly attach an older task to the currently captured app/tab. |

Creating a task:

```json
{"title":"Review the architecture", "status":"ongoing"}
```

## Controlled desktop tools

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/apps` | Lists approved app IDs. |
| `POST` | `/api/os/app` | Opens an app by allowlisted `app_id`. |
| `POST` | `/api/os/terminal` | Opens the approved terminal only. |
| `POST` | `/api/browser/open` | Opens a validated HTTP(S) URL in Google Chrome (or the system browser only when Chrome is unavailable). |
| `POST` | `/api/browser/summarize` | Local, explicit-consent page summary. |

`/api/os/app` never accepts executable paths, shell commands, or arbitrary application names. Current approved IDs are `terminal`, `vscode`, `browser`, `calculator`, `notes`, `word`, and `files`.

## Notifications and writing

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` / `GET` | `/api/notifications` | Ingest/list summarized notifications. |
| `PATCH` / `DELETE` | `/api/notifications/{id}/review` / `{id}` | Mark reviewed/delete. |
| `POST` / `GET` | `/api/writing/analyze` / `/api/writing/suggestions` | Explicit, local writing assistance/list. |
| `PATCH` / `DELETE` | `/api/writing/suggestions/{id}/review` / `{id}` | Mark reviewed/delete. |

Writing analysis requires `consent: true` and an `operation` of `summarize`, `improve`, `explain`, or `ideas`. It returns local improvement text plus extracted `keywords` and `related_queries`; Chrome receives a query only after the user selects one.

The Word add-in is an authenticated client of this endpoint. It obtains text through `Office.context.document.getSelectedDataAsync` only after a button click; it does not receive or submit the rest of the document.

When an opted-in state source reports a recognised document context, planner suggestions include `related_queries`: text topics for documentation, examples, and best practices derived from the title only. Choosing a topic launches Chrome; the planner does not background-fetch it.

## Settings

`GET /api/settings` returns non-secret privacy and retention settings. It never returns `API_TOKEN`, database paths, or provider keys.
