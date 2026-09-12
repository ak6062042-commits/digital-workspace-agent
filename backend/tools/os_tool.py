"""Controlled desktop launching. No user input is ever passed to a shell."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("OSTool")

APP_ALLOWLIST = {
    "terminal": {"label": "Terminal", "darwin": ["open", "-a", "Terminal"], "win32": ["cmd.exe"], "linux": ["x-terminal-emulator"]},
    "vscode": {
        "label": "Visual Studio Code",
        "darwin": ["open", "-a", "Visual Studio Code"],
        "win32": ["code"],
        "win32_candidates": ["Programs/Microsoft VS Code/Code.exe", "Microsoft VS Code/Code.exe"],
        "linux": ["code"],
    },
    "browser": {
        "label": "Google Chrome",
        "darwin": ["open", "-a", "Google Chrome"],
        "win32": ["chrome.exe"],
        "win32_candidates": ["Google/Chrome/Application/chrome.exe"],
        "linux": ["google-chrome"],
    },
    "calculator": {"label": "Calculator", "darwin": ["open", "-a", "Calculator"], "win32": ["calc.exe"], "linux": ["gnome-calculator"]},
    "notes": {"label": "Notes", "darwin": ["open", "-a", "Notes"], "win32": ["notepad.exe"], "linux": ["gedit"]},
    "word": {
        "label": "Microsoft Word",
        "darwin": ["open", "-a", "Microsoft Word"],
        "win32": ["winword.exe"],
        "win32_candidates": [
            "Microsoft Office/root/Office16/WINWORD.EXE",
            "Microsoft Office/Office16/WINWORD.EXE",
        ],
        "linux": None,
    },
    "files": {"label": "File Manager", "darwin": ["open", "."], "win32": ["explorer.exe", "."], "linux": ["xdg-open", "."]},
}

ALIASES = {
    "console": "terminal", "iterm": "terminal", "code": "vscode", "vs code": "vscode",
    "visual studio code": "vscode", "code.exe": "vscode", "chrome": "browser", "google chrome": "browser", "chrome.exe": "browser",
    "finder": "files", "file manager": "files", "explorer": "files", "explorer.exe": "files", "calc": "calculator", "calc.exe": "calculator",
    "microsoft word": "word", "ms word": "word", "winword": "word", "winword.exe": "word",
}


def list_allowed_apps() -> list[dict[str, str]]:
    return [{"id": key, "label": value["label"]} for key, value in APP_ALLOWLIST.items()]


def normalize_app_id(app_name: str) -> str | None:
    candidate = (app_name or "").strip().lower()
    return ALIASES.get(candidate, candidate if candidate in APP_ALLOWLIST else None)


def _platform_command(spec: dict[str, Any]) -> list[str] | None:
    """Resolve only fixed, known Office locations; never accept a user path."""
    if sys.platform == "win32":
        for relative_path in spec.get("win32_candidates", []):
            for base_dir in (os.environ.get("LOCALAPPDATA"), os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)")):
                if base_dir:
                    candidate = Path(base_dir, relative_path)
                    if candidate.is_file():
                        return [str(candidate)]
    return spec.get(sys.platform)


def open_desktop_app(app_name: str) -> dict[str, Any]:
    app_id = normalize_app_id(app_name)
    if not app_id:
        return {"success": False, "error": "Application is not in the approved allowlist", "allowed_apps": list_allowed_apps()}
    spec = APP_ALLOWLIST[app_id]
    command = _platform_command(spec)
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
