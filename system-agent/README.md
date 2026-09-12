# System agent and browser companion

## Local state watcher

`local-agent/watcher.py` collects only active application, window title, and—where a supported platform adapter exposes it—browser URL/title. It does not capture screenshots, clipboard data, or keystrokes.

It is disabled by default. To use it:

1. Run `scripts/setup.*` to create `.env` and the API token.
2. Set `CAPTURE_ENABLED=true` in `.env` after reviewing the privacy implications.
3. Run `python system-agent/local-agent/watcher.py` from the activated virtual environment.

The watcher sends `X-Workspace-Token` to the local API. If the backend is unavailable, its direct SQLite fallback remains local to the project database.

Platform support:

- macOS: active app/window; active tab URL/title requires the OS Automation permission.
- Windows: active foreground application and window title.
- Linux/X11: active window metadata through `xdotool`.

## Browser extension

Load `browser-extension` unpacked in a Chromium browser. The extension:

- has no content script and does not observe text input;
- requires a user-provided local API token in its popup;
- optionally synchronizes active-tab metadata after the user enables that setting;
- summarizes a page or analyzes selected text only after a user click; selected-text analysis returns a rewrite, extracted keywords, and user-triggered related-document searches in Chrome.

The extension has access to the active tab only for these explicit interactions. Do not enable state sync on a browser profile that contains workspaces you do not intend to store locally.

## Floating widget

`floating-widget/widget.py` is an optional, roomier PyQt command center. It displays the current permitted workspace metadata, active tasks, notifications, planner topics, and explicit writing improvements. Its chat field accepts requests such as **Open this tab**, **Open VS Code**, or **Research this current topic**; each goes through the same planner, allowlist, and confirmation policy as the dashboard. The watcher recognises this window and never stores it as `python.exe` workspace state.

Run it after the backend is available:

```powershell
.venv\Scripts\python system-agent\floating-widget\widget.py
```

It is a client of the same authenticated API and does not create independent automation rules.

## Word writing assistant

`word-addin` is a local Word task-pane add-in. It sends only user-selected text after the **Analyze selected text** button is clicked. See [word-addin/README.md](word-addin/README.md) for sideloading instructions.
