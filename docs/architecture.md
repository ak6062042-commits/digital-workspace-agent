# Architecture

## Design rule

The assistant follows a controlled feedback loop:

```
Observe -> extract minimal state -> plan -> validate policy -> execute -> report -> observe
```

The user is the authority for consequential actions. LLM output, webpage content, search snippets, and natural-language requests never receive direct computer-control access.

## Components

| Component | Location | Responsibility |
| --- | --- | --- |
| State estimator | `system-agent/local-agent`, `backend/agents/state_agent.py` | Captures opted-in app/window/tab metadata; stores structured snapshots; provides diffs. |
| Planner | `backend/orchestration/planner.py` | Converts a request and current state into a typed `ExecutionPlan`. It performs no side effects. |
| Executor | `backend/orchestration/executor.py` | Enforces plan category/confirmation policy and invokes approved tools only. |
| Tools | `backend/tools`, `backend/agents` | Implement browser opening, allowlisted app launch, task operations, and research. |
| API | `backend/main.py` | Authenticated local transport, input bounds, retention, and resource APIs. |
| Dashboard | `frontend/src` | Shows chat, state, tasks, notifications, writing assistance, planner proposals, and privacy state. |

## Plan categories

| Category | Examples | Behaviour |
| --- | --- | --- |
| `observe` | state lookup, state diff, task list | Runs without changing workspace state. |
| `assist` | create task, approved app launch | Runs only through a declared safe tool. |
| `hybrid` | web research | Retrieves and summarizes research; external navigation remains user-controlled. |
| `consequential` | send, submit, delete, install | Not implemented as automatic tools. Executor stores a confirmation proposal first. |

## State and persistence

SQLite stores four structured models:

- `state_snapshots`: app, window title, browser URL/title, capture time.
- `tasks`: title, description, due date, `pending`/`ongoing`/`done` state.
- `notifications`: minimized source and summary; raw content is not returned by normal list calls.
- `writing_suggestions`: explicitly submitted, redacted excerpts and local suggestions.

On startup, the database enables WAL, a ten-second busy timeout, foreign keys, forward-only task migrations, and retention cleanup. Snapshots default to 14 days; notification and writing records default to 30 days.

## Security boundary

```
Dashboard / Local agent / Extension / Widget
             | X-Workspace-Token
             v
  loopback FastAPI + strict CORS + request/rate bounds
             v
       Planner -> Executor -> allowlisted tool
```

- `API_TOKEN` is required for every API route except `/health`.
- `BACKEND_HOST` must be loopback unless Docker explicitly sets its container-only exception.
- The extension stores its locally configured token in extension storage and makes authenticated calls only to loopback.
- Generic shell command execution and arbitrary application launch are absent.
- Rendered Markdown discards raw HTML and unsafe link schemes.

## Browser and writing privacy

The browser extension has no background content script and does not listen for input events. It injects a short-lived script only after the user presses **Summarize Tab** or **Analyze selected text**. Writing analysis requires consent in the payload, redacts common secrets/PII locally, and does not query external search services.

## Platform adapters

The local watcher uses platform-specific state functions behind `capture_snapshot()`:

- macOS: AppleScript app/window metadata and active browser tab data with OS-granted permissions.
- Windows: foreground process and window title via `user32`; browser URL needs the companion extension.
- Linux/X11: `xdotool` active window metadata. Wayland is not supported yet.

No screenshots, clipboard data, or keystrokes are collected.
