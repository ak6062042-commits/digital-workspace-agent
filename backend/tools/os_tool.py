import os
import sys
import logging
import subprocess
from typing import Dict, Any, Optional

logger = logging.getLogger("OSTool")


def open_terminal(command: Optional[str] = None) -> Dict[str, Any]:
    """
    Launch or activate the native Terminal application.
    On macOS: uses AppleScript or open -a Terminal.
    Optionally runs a command if provided.
    """
    try:
        if sys.platform == "darwin":
            if command:
                # Run command in a new Terminal window
                clean_cmd = command.replace('"', '\\"')
                script = f'''
                tell application "Terminal"
                    activate
                    do script "{clean_cmd}"
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=False)
                logger.info("Opened Terminal with command: %s", command)
            else:
                script = 'tell application "Terminal" to activate'
                subprocess.run(["osascript", "-e", script], check=False)
                logger.info("Activated Terminal on macOS")
            return {"success": True, "app": "Terminal", "command": command}

        elif sys.platform == "win32":
            subprocess.Popen(["cmd.exe"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            return {"success": True, "app": "Command Prompt", "command": command}

        else:
            subprocess.Popen(["x-terminal-emulator"])
            return {"success": True, "app": "Terminal", "command": command}

    except Exception as err:
        logger.error("Failed to open terminal: %s", err)
        return {"success": False, "error": str(err)}


def open_desktop_app(app_name: str) -> Dict[str, Any]:
    """
    Open or activate any native desktop application.
    Handles common names like 'Terminal', 'Finder', 'VS Code', 'Visual Studio Code',
    'Notes', 'Calculator', 'Spotify', 'Chrome', etc.
    """
    import re

    norm_name = app_name.strip()
    norm_lower = norm_name.lower()

    if "terminal" in norm_lower or "console" in norm_lower or "iterm" in norm_lower:
        return open_terminal()

    # Clean leading verbs like "open ", "launch ", "start ", "run ", "the ", "my "
    clean_target = re.sub(r'^(open|launch|start|run)\s+(the\s+|my\s+)?', '', norm_lower).strip()

    try:
        if sys.platform == "darwin":
            # Map friendly names to macOS application names
            app_map = {
                "vs code": "Visual Studio Code",
                "vscode": "Visual Studio Code",
                "code": "Visual Studio Code",
                "visual studio code": "Visual Studio Code",
                "visual studio": "Visual Studio Code",
                "finder": "Finder",
                "notes": "Notes",
                "calculator": "Calculator",
                "calc": "Calculator",
                "chrome": "Google Chrome",
                "google chrome": "Google Chrome",
                "safari": "Safari",
                "spotify": "Spotify",
                "slack": "Slack",
                "sublime": "Sublime Text",
                "sublime text": "Sublime Text",
                "cursor": "Cursor",
                "warp": "Warp",
            }
            target = app_map.get(clean_target, app_map.get(norm_lower, norm_name))

            script = f'''
            tell application "{target}"
                activate
            end tell
            '''
            proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
            if proc.returncode == 0:
                logger.info("Activated application via AppleScript: %s", target)
                return {"success": True, "app": target}

            # Fallback to open -a
            subprocess.run(["open", "-a", target], check=False)
            return {"success": True, "app": target}

        elif sys.platform == "win32":
            subprocess.run(["start", clean_target or norm_name], shell=True, check=False)
            return {"success": True, "app": clean_target or norm_name}

        else:
            subprocess.Popen([clean_target or norm_lower])
            return {"success": True, "app": clean_target or norm_name}

    except Exception as err:
        logger.error("Failed to open desktop application %s: %s", app_name, err)
        return {"success": False, "app": app_name, "error": str(err)}


if __name__ == "__main__":
    res = open_terminal()
    print("Terminal test:", res)
