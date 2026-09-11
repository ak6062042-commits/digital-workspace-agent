import logging
from typing import Optional
import requests

try:
    import trafilatura
except ImportError:
    trafilatura = None

logger = logging.getLogger("FetchTool")


def fetch_webpage_content(url: str, max_chars: int = 3000, timeout: float = 4.0) -> str:
    """
    Fetch a webpage URL and extract clean, readable text using trafilatura.
    Truncates to max_chars to keep context window tight.
    """
    if not url or not url.startswith(("http://", "https://")):
        return f"Error: Invalid URL '{url}'"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return f"Failed to fetch {url}: HTTP {resp.status_code}"

        html = resp.text

        if trafilatura is not None:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )
            if extracted:
                clean_text = extracted.strip()
                if len(clean_text) > max_chars:
                    return clean_text[:max_chars] + "\n\n...[Content truncated for brevity]..."
                return clean_text

        # Fallback: simple text extraction if trafilatura isn't available or returned empty
        import re
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]

    except requests.exceptions.Timeout:
        return f"Error: Request timed out fetching {url}"
    except Exception as err:
        logger.warning("Error fetching URL %s: %s", url, err)
        return f"Error fetching {url}: {str(err)}"


if __name__ == "__main__":
    content = fetch_webpage_content("https://example.com")
    print(content)
