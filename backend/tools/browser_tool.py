import os
import sys
import logging
import subprocess
import urllib.parse
import webbrowser
from typing import Optional, Dict, Any

logger = logging.getLogger("BrowserTool")


def open_url_in_browser(url: str, bring_to_front: bool = True) -> bool:
    """
    Open a URL in the user's default browser or Google Chrome, and optionally bring it to the front.
    Fully compatible with macOS, Windows, and Linux.
    """
    if not url or not url.startswith(("http://", "https://")):
        logger.warning("Invalid URL passed to browser tool: %s", url)
        return False

    try:
        # On macOS, preferentially launch via Google Chrome or default browser using 'open' command
        if sys.platform == "darwin":
            # Attempt to open in Google Chrome first if available, else system default
            chrome_app = "/Applications/Google Chrome.app"
            if os.path.exists(chrome_app):
                subprocess.run(["open", "-a", "Google Chrome", url], check=False)
                if bring_to_front:
                    # AppleScript to bring Chrome to front
                    script = 'tell application "Google Chrome" to activate'
                    subprocess.run(["osascript", "-e", script], check=False)
                logger.info("Opened URL in Google Chrome (macOS): %s", url)
                return True
            else:
                subprocess.run(["open", url], check=False)
                logger.info("Opened URL in default browser (macOS): %s", url)
                return True

        elif sys.platform == "win32":
            os.startfile(url)
            logger.info("Opened URL in default browser (Windows): %s", url)
            return True

        else:
            # Linux fallback
            subprocess.run(["xdg-open", url], check=False)
            logger.info("Opened URL in default browser (Linux): %s", url)
            return True

    except Exception as e:
        logger.warning("Failed to open URL using platform command (%s). Falling back to python webbrowser.", e)
        try:
            webbrowser.open_new_tab(url)
            return True
        except Exception as err:
            logger.error("webbrowser.open failed: %s", err)
            return False


def search_in_browser(query: str, engine: str = "google", bring_to_front: bool = True) -> Dict[str, Any]:
    """
    Construct a live search URL and open it in the user's real desktop browser.
    """
    encoded_query = urllib.parse.quote(query.strip())
    
    if engine.lower() == "duckduckgo":
        search_url = f"https://duckduckgo.com/?q={encoded_query}"
    elif engine.lower() == "bing":
        search_url = f"https://www.bing.com/search?q={encoded_query}"
    else:
        search_url = f"https://www.google.com/search?q={encoded_query}"

    success = open_url_in_browser(search_url, bring_to_front=bring_to_front)
    return {
        "success": success,
        "query": query,
        "search_url": search_url,
        "engine": engine
    }


if __name__ == "__main__":
    res = search_in_browser("Railway vs Vercel comparison 2026")
    print(res)
