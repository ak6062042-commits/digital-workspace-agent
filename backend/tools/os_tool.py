"""Controlled desktop launching. No user input is ever passed to a shell."""
from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger("OSTool")

APP_ALLOWLIST = {
    "terminal": {"label": "Terminal", "darwin": ["open", "-a", "Terminal"], "win32": ["cmd.exe"], "linux": ["x-terminal-emulator"]},
    "vscode": {"label": "Visual Studio Code", "darwin": ["open", "-a", "Visual Studio Code"], "win32": ["code"], "linux": ["code"]},
    "browser": {"label": "Web Browser", "darwin": ["open", "-a", "Google Chrome"], "win32": ["cmd.exe", "/c", "start", "", "https://www.google.com"], "linux": ["xdg-open", "https://www.google.com"]},
    "calculator": {"label": "Calculator", "darwin": ["open", "-a", "Calculator"], "win32": ["calc.exe"], "linux": ["gnome-calculator"]},
    "notes": {"label": "Notes", "darwin": ["open", "-a", "Notes"], "win32": ["notepad.exe"], "linux": ["gedit"]},
    "files": {"label": "File Manager", "darwin": ["open", "."], "win32": ["explorer.exe", "."], "linux": ["xdg-open", "."]},
}

ALIASES = {
    "console": "terminal", "iterm": "terminal", "code": "vscode", "vs code": "vscode",
    "visual studio code": "vscode", "chrome": "browser", "google chrome": "browser",
    "finder": "files", "file manager": "files", "calc": "calculator",
}


def list_allowed_apps() -> list[dict[str, str]]:
    return [{"id": key, "label": value["label"]} for key, value in APP_ALLOWLIST.items()]


def normalize_app_id(app_name: str) -> str | None:
    candidate = (app_name or "").strip().lower()
    return ALIASES.get(candidate, candidate if candidate in APP_ALLOWLIST else None)


def open_desktop_app(app_name: str) -> dict[str, Any]:
    app_id = normalize_app_id(app_name)
    if not app_id:
        return {"success": False, "error": "Application is not in the approved allowlist", "allowed_apps": list_allowed_apps()}
    spec = APP_ALLOWLIST[app_id]
    command = spec.get(sys.platform)
    if not command:
        return {"success": False, "error": f"{spec['label']} is not supported on this platform"}
    try:
        subprocess.Popen(command, shell=False)
        return {"success": True, "app": spec["label"], "app_id": app_id}
    except OSError as error:
        logger.warning("Could not launch approved application %s: %s", app_id, error)
        return {"success": False, "app": spec["label"], "error": str(error)}


def open_terminal() -> dict[str, Any]:
    return open_desktop_app("terminal")
