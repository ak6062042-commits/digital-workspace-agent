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
- summarizes a page or analyzes selected text only after a user click.

The extension has access to the active tab only for these explicit interactions. Do not enable state sync on a browser profile that contains workspaces you do not intend to store locally.

## Floating widget

`floating-widget/widget.py` is an optional PyQt tray-like interface. Run it in an environment with `PyQt5` installed and `API_TOKEN` available. It is a client of the same authenticated API and does not create independent automation rules.
