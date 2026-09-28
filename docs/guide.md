# Digital Workspace Agent power-user guide

This guide shows how to use the complete local workspace system together: dashboard, chat, research, task board, optional context capture, Chrome companion, Word add-in, and desktop widget. Start with the core workflow, then add only the companions that make your daily work easier.

## 1. What to run

The project has one backend and several optional clients. The backend must be running for every client below.

| Component | Use it for | Required? |
| --- | --- | --- |
| FastAPI backend | API, planning, persistence, research, and companion integrations | Yes |
| React dashboard | Full daily workspace, chat, tasks, research, writing, notifications | Recommended |
| Local watcher | Current app/window context in the workspace timeline | Optional |
| Chrome companion | Accurate Chrome-tab context, page summaries, selected-text analysis | Optional |
| Word add-in | Analyze the currently selected Word text | Optional |
| PyQt widget | Always-available compact command center | Optional |

## 2. First-time setup

### Windows

From the repository root, run:

```bat
scripts\setup.bat
```

The setup script creates `.venv`, prepares `.env`, generates or preserves the local API token, installs Python dependencies, initializes SQLite, and installs frontend packages when npm is installed.

Open two terminals and run:

```bat
scripts\run_backend.bat
```

```bat
scripts\run_frontend.bat
```

Open `http://localhost:5173`. Confirm the backend is ready at `http://127.0.0.1:8000/health`.

### macOS or Linux

```bash
./scripts/setup.sh
./scripts/run_backend.sh
./scripts/run_frontend.sh
```

Windows is the most complete watcher target. Linux watcher support currently requires X11 and `xdotool`; Wayland is not supported by the watcher.

## 3. Configure the features you want

Edit the generated `.env` file, then restart the backend after changing a backend setting.

```env
# Best live-research experience
EXA_API_KEY=your_exa_api_key
WEB_SEARCH_PROVIDER=exa

# Optional current-workspace timeline
CAPTURE_ENABLED=true

# Useful personal-workflow defaults
RESEARCH_MAX_RESULTS=6
RESEARCH_FETCH_RESULTS=4
RESEARCH_MAX_CHARS=6000
SNAPSHOT_RETENTION_DAYS=14
CONTENT_RETENTION_DAYS=30
```

`EXA_API_KEY` makes Exa the primary research provider. If it is not set, invalid, or temporarily unavailable, the project automatically falls back to DuckDuckGo and then Bing RSS. Set `WEB_SEARCH_PROVIDER=chrome`, `browser`, or `manual` when you want browser-only research with no retrieved or summarized sources.

Keep `API_TOKEN` and `VITE_API_TOKEN` matching. The setup script manages this for a new installation. Never paste either token into chat messages, research queries, or public issue trackers.

## 4. The highest-value daily workflow

Use this loop to get the most from the project without needing every optional integration.

1. Start the backend and dashboard.
2. Open the project, page, or document you are working on.
3. Capture context with the optional watcher/Chrome sync, or work without capture if you prefer a manual workflow.
4. In the dashboard, create a task for the outcome—not just the next click. For example: `Create task: publish the API migration guide`.
5. Link the task to the current app or tab using **Link current app/tab** if it does not already have context.
6. Move the task to **Ongoing** while working. Use the task’s context link later to reopen its saved tab when available.
7. Use the quick-research panel or chat for facts, comparisons, and documentation. Inspect source domains before opening a result.
8. Paste a draft into **Writing workbench** for a local improvement, summary, explanation, or idea generation pass.
9. Mark suggestions, notifications, and completed tasks reviewed or done so the overview stays useful.

Good command examples:

```text
What was I working on?
What changed while I was away?
Create task: compare Redis persistence options
Show my active tasks
Complete task 3
Research FastAPI deployment patterns
Compare Obsidian, Logseq, and Notion for offline technical notes
Open VS Code
Open this tab
```

The assistant plans each message before it acts. Review any confirmation card before a consequential action is allowed to proceed.

## 5. Use research well

### Fast research from the dashboard

Use **Quick research** in the workspace panel for a focused question. The response contains:

- a short source-attributed brief;
- the provider used (`Exa` or a named fallback);
- source cards with title, domain, and extractive summary;
- a browser search when the research plan requests it.

Write specific prompts for stronger results:

```text
Research official FastAPI deployment guidance for a small Windows-hosted service
Compare current Python task schedulers for a personal desktop automation tool
Find primary documentation for Exa Search API inline text results
Research practical SQLite WAL backup strategies for a local FastAPI app
```

For a broad subject, do two or three distinct requests instead of one vague one: fundamentals, current options, and implementation details. Treat all retrieved text and links as untrusted until you inspect the source yourself.

### Research from existing work

The writing workbench and Word add-in create related research queries from the text you explicitly submit. Select one of those **Research:** buttons to turn a draft into a focused fact-finding task.

Planner suggestions can also offer related queries when the workspace has been focused on an eligible document-like context. Use a suggested query when relevant, or dismiss it to keep the panel clear.

## 6. Get more out of tasks and context

The task board supports **Pending**, **Ongoing**, and **Done** states. Use it as a lightweight, context-aware queue:

- Create tasks in the board for a title, optional description, and due date.
- Create tasks in chat when you are already describing the work.
- Use **Link current app/tab** before leaving a task behind; this is the best way to make a task resumable.
- Use the context link beside a task to reopen its saved browser URL when the task has valid browser context.
- Filter completed work out of view when you want a smaller active queue.
- Use `What was I working on?` after switching contexts or returning to the computer.

A task can only reopen context that was captured before it was created or explicitly linked later. If a task has no context, focus the relevant app or browser tab, allow a new snapshot to arrive, then choose **Link current app/tab**.

## 7. Turn on workspace awareness

The watcher is optional. It records the active application, window title, and available browser metadata—not screenshots, keystrokes, clipboard data, or document contents.

1. Set `CAPTURE_ENABLED=true` in `.env`.
2. Restart the backend.
3. In an activated virtual environment, run:

   ```powershell
   .venv\Scripts\python system-agent\local-agent\watcher.py
   ```

4. Work normally, then use the dashboard’s workspace status, recent history, and state diff to orient yourself.

The watcher deduplicates equivalent states and sends snapshots only through the authenticated backend. The widget’s own window is ignored so it cannot overwrite the current work context.

## 8. Add the Chrome companion

The extension is the best way to add accurate Chrome-tab context and explicit in-browser analysis.

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Choose **Load unpacked** and select `system-agent/browser-extension`.
4. Open the extension popup.
5. Paste `API_TOKEN` from `.env` and save settings.
6. Enable **Sync active tab** only when you want Chrome title/URL metadata in the workspace timeline.

Use its three deliberate actions:

| Control | Best use |
| --- | --- |
| **Sync now** | Save the active tab as current workspace context before creating/linking a task. |
| **Summarize Tab** | Get a local extractive summary, takeaways, and keywords for the active page. |
| **Analyze selected text** | Improve selected page text and receive related searches. |

The extension does not silently capture page content. Summary and selection actions operate only after you press their respective button. Reload the extension from `chrome://extensions` after changing extension files.

## 9. Use Word for writing and research

The Word add-in is ideal for turning an active draft into a concise improvement or a research plan.

1. Start the backend.
2. In Word for Windows, go to **Home → Add-ins → More Add-ins → My Add-ins → Upload My Add-in**.
3. Select `system-agent/word-addin/manifest.xml`.
4. Open the **Workspace Writing Assistant** task pane.
5. Enter the local `API_TOKEN` once.
6. Select text, choose an operation, and click **Analyze selected text**.

Choose the operation that matches the draft stage:

| Operation | Use it when you need |
| --- | --- |
| Improve | Clearer, more actionable wording. |
| Summarize | A compact account of a longer selection. |
| Explain | Plainer language for technical or dense text. |
| Ideas | Follow-up angles, gaps, or next steps. |

The task pane reads the Word selection only after you press Analyze. Related-query buttons open the selected query in Chrome. Reopen the pane after changing add-in files so Word does not keep an older cached version.

## 10. Use the floating widget as a command center

With the backend running, launch the widget:

```powershell
.venv\Scripts\python system-agent\floating-widget\widget.py
```

Click the floating icon to open the panel. Drag the icon to position it. The panel offers:

- **Today**: current context, active tasks, task status changes, context linking, and reopen actions;
- **Research**: a compact research brief with explicit source buttons;
- **Inbox & Writing**: notifications and writing suggestions;
- quick chat commands and **Research current topic**;
- dashboard opening and manual refresh.

Use the widget when the dashboard would interrupt your flow. It reads the same overview and sends the same authenticated chat requests, so it stays in sync with the browser dashboard.

## 11. Voice and notifications

### Voice in the dashboard

Click the microphone to enable voice recognition. In supported Chromium browsers, say **“Hey Agent”**, then your command. The transcript is placed in the composer for review; it does not send or execute until you press **Send**. Use the speaker button to enable or mute spoken responses.

### Notification inbox

The dashboard and widget show unread notification records stored through the authenticated API. Review an item to clear it from the active inbox, or delete it when it is no longer useful. This repository does not connect directly to WhatsApp, email, or native OS notifications; those records must be supplied through an intentional integration or API client.

## 12. Use the API for your own automations

Every `/api/*` request requires the local token:

```http
X-Workspace-Token: <API_TOKEN>
```

Useful integration points include:

| Goal | Endpoint |
| --- | --- |
| Chat/planning | `POST /api/chat` |
| Current dashboard data | `GET /api/workspace/overview` |
| Create or update a task | `POST /api/tasks`, `PATCH /api/tasks/{id}` |
| Supply workspace context | `POST /api/snapshot` |
| Analyze supplied writing | `POST /api/writing/analyze` |
| Add a notification record | `POST /api/notifications` |
| Inspect configuration state | `GET /api/settings` |

Use the documented request shapes in [API contracts](api-contracts.md). The API rejects unexpected fields, and `GET /health` is the only endpoint that does not require the token.

## 13. Practical maintenance

Use these checks after upgrades or code changes:

```bat
scripts\test.bat
```

Or run them manually from the repository root:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall backend system-agent
Set-Location frontend
npm run build
```

To explore the complete interface quickly, use the seed scripts intentionally:

```bat
scripts\seed_demo_data.bat
```

For local containers, generate/verify `.env` first, then run `docker compose up --build`. The host-facing dashboard and backend ports remain loopback by default.

## 14. A full-feature day in ten minutes

1. Start backend, frontend, watcher, and widget.
2. Configure the Chrome extension and sync the page you are beginning from.
3. Create a task linked to that context.
4. Research the key unknown with Exa; inspect the brief’s cited sources.
5. Move the task to Ongoing and open the saved context when switching back.
6. Use the Chrome companion to summarize a long reference page.
7. Paste your notes into the dashboard writing workbench, then choose a related research query to fill gaps.
8. In Word, select the finished draft section and use Improve or Explain for a final pass.
9. Mark the writing suggestion reviewed and task done.
10. Use `What changed while I was away?` or the workspace diff to restart cleanly next time.

For the underlying design, limits, and troubleshooting details, see [README](../README.md), [architecture](architecture.md), and [API contracts](api-contracts.md).
