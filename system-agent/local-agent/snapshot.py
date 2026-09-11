import os
import sys
import json
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from config import OS_PLATFORM, HOSTNAME
except ImportError:
    from .config import OS_PLATFORM, HOSTNAME


def _run_applescript(script: str, timeout: float = 2.0) -> Optional[str]:
    """Execute an AppleScript string via osascript and return stripped stdout."""
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return None


def _get_macos_browser_tab(app_name: str) -> Dict[str, Optional[str]]:
    """Query active browser tab URL and title on macOS."""
    browser_data = {"browser_url": None, "browser_tab_title": None}
    normalized = app_name.lower()

    script = None
    if "chrome" in normalized or "brave" in normalized or "edge" in normalized:
        # Chromium-based apps support standard AppleScript syntax
        script = f'''
        tell application "{app_name}"
            if (count of windows) > 0 then
                set activeTab to active tab of front window
                return (get URL of activeTab) & ":::" & (get title of activeTab)
            end if
        end tell
        '''
    elif "safari" in normalized:
        script = '''
        tell application "Safari"
            if (count of windows) > 0 then
                set currentDoc to current tab of front window
                return (get URL of currentDoc) & ":::" & (get name of currentDoc)
            end if
        end tell
        '''
    elif "arc" in normalized:
        script = '''
        tell application "Arc"
            if (count of windows) > 0 then
                set activeTab to active tab of front window
                return (get URL of activeTab) & ":::" & (get title of activeTab)
            end if
        end tell
        '''

    if script:
        output = _run_applescript(script)
        if output and ":::" in output:
            parts = output.split(":::", 1)
            browser_data["browser_url"] = parts[0].strip() or None
            browser_data["browser_tab_title"] = parts[1].strip() or None

    return browser_data


def _get_macos_state() -> Dict[str, Any]:
    """Capture frontmost window and application on macOS."""
    script = '''
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        set frontAppName to name of frontApp
        set windowTitle to ""
        try
            tell frontApp
                if (count of windows) > 0 then
                    set windowTitle to name of front window
                end if
            end tell
        end try
        if windowTitle is "" then
            try
                tell frontApp
                    if (count of windows) > 0 then
                        set windowTitle to title of front window
                    end if
                end tell
            end try
        end if
        if windowTitle is "" then
            try
                tell frontApp
                    if (count of windows) > 0 then
                        set windowTitle to value of attribute "AXTitle" of front window
                    end if
                end tell
            end try
        end if
        return frontAppName & ":::" & windowTitle
    end tell
    '''
    active_app = None
    window_title = None

    res = _run_applescript(script)
    if res and ":::" in res:
        parts = res.split(":::", 1)
        active_app = parts[0].strip() or None
        window_title = parts[1].strip() or None

    # If frontmost app is a browser, get current tab information
    browser_data = {"browser_url": None, "browser_tab_title": None}
    if active_app:
        browser_data = _get_macos_browser_tab(active_app)

    return {
        "active_app": active_app,
        "active_window_title": window_title,
        "browser_url": browser_data.get("browser_url"),
        "browser_tab_title": browser_data.get("browser_tab_title"),
    }


def _get_windows_state() -> Dict[str, Any]:
    """Capture frontmost window on Windows using ctypes without external deps."""
    active_app = None
    window_title = None

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            # Window title
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            window_title = buff.value or None

            # Process Name
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                try:
                    import psutil
                    proc = psutil.Process(pid.value)
                    active_app = proc.name()
                except Exception:
                    pass
    except Exception:
        pass

    return {
        "active_app": active_app or "Windows Application",
        "active_window_title": window_title,
        "browser_url": None,
        "browser_tab_title": None,
    }


def _get_linux_state() -> Dict[str, Any]:
    """Capture active window using xdotool if available on Linux."""
    active_app = None
    window_title = None

    try:
        proc = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if proc.returncode == 0:
            window_title = proc.stdout.strip()

        proc_cls = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowclassname"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if proc_cls.returncode == 0:
            active_app = proc_cls.stdout.strip()
    except Exception:
        pass

    return {
        "active_app": active_app or "Linux Desktop",
        "active_window_title": window_title,
        "browser_url": None,
        "browser_tab_title": None,
    }


def capture_snapshot() -> Dict[str, Any]:
    """
    Capture the current OS and browser state snapshot.
    Conforms to shared/schemas/state_snapshot.json.
    """
    if OS_PLATFORM == "darwin":
        state = _get_macos_state()
    elif OS_PLATFORM == "win32":
        state = _get_windows_state()
    else:
        state = _get_linux_state()

    now_iso = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "active_app": state.get("active_app"),
        "active_window_title": state.get("active_window_title"),
        "browser_url": state.get("browser_url"),
        "browser_tab_title": state.get("browser_tab_title"),
        "captured_at": now_iso,
        "metadata": {
            "os_platform": OS_PLATFORM,
            "hostname": HOSTNAME,
            "source": "local-agent",
        },
    }
    return snapshot


if __name__ == "__main__":
    snap = capture_snapshot()
    print(json.dumps(snap, indent=2))
