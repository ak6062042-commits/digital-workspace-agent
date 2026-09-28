"""Readable page extraction for live personal research."""
from __future__ import annotations

import logging
import re
import ipaddress
import socket
from html import unescape
from urllib.parse import urljoin, urlparse

import requests

try:
    import trafilatura
except ImportError:
    trafilatura = None

logger = logging.getLogger("FetchTool")
_USER_AGENT = "DigitalWorkspaceAgent/2.1 (+local personal research)"
_MAX_DOWNLOAD_BYTES = 1_500_000


def _plain_text_from_html(html: str) -> str:
    html = re.sub(r"<(script|style|noscript|svg|nav|header|footer|aside)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def is_safe_research_url(url: str) -> bool:
    """Keep automated retrieval on public HTTP(S) destinations only."""
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return False
    host = parsed.hostname.strip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        pass
    try:
        resolved = {address[4][0] for address in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
    except socket.gaierror:
        return False
    try:
        return bool(resolved) and all(ipaddress.ip_address(address).is_global for address in resolved)
    except ValueError:
        return False


def fetch_webpage_content(url: str, max_chars: int = 6000, timeout: float = 8.0) -> str:
    """Fetch an HTTP(S) page and return readable extracted text for synthesis."""
    if not is_safe_research_url(url):
        return f"Error: Invalid URL '{url}'"
    try:
        current_url = url
        response = None
        for _redirect in range(4):
            if not is_safe_research_url(current_url):
                return "Error: The page redirected to a non-public destination."
            response = requests.get(
                current_url,
                headers={"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.3"},
                timeout=timeout,
                stream=True,
                allow_redirects=False,
            )
            if response.is_redirect:
                location = response.headers.get("location")
                response.close()
                if not location:
                    return f"Failed to fetch {url}: redirect without a destination"
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            break
        else:
            return f"Failed to fetch {url}: too many redirects"
        if response is None:
            return f"Failed to fetch {url}: no response"
        content_type = response.headers.get("content-type", "").lower()
        if content_type and not any(kind in content_type for kind in ("text/", "html", "xml")):
            response.close()
            return f"Failed to fetch {url}: unsupported content type {content_type.split(';', 1)[0]}"
        chunks: list[bytes] = []
        received = 0
        for chunk in response.iter_content(chunk_size=32768):
            if not chunk:
                continue
            chunks.append(chunk)
            received += len(chunk)
            if received >= _MAX_DOWNLOAD_BYTES:
                break
        html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
        response.close()
    except requests.exceptions.Timeout:
        return f"Error: Request timed out fetching {url}"
    except requests.RequestException as error:
        logger.info("Could not fetch %s: %s", url, error)
        return f"Failed to fetch {url}: {error}"

    extracted = ""
    if trafilatura is not None:
        try:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_recall=True,
            ) or ""
        except (TypeError, ValueError) as error:
            logger.info("Trafilatura extraction failed for %s: %s", url, error)
    text = re.sub(r"\s+", " ", extracted or _plain_text_from_html(html)).strip()
    if not text:
        return f"Failed to extract readable content from {url}"
    if len(text) > max_chars:
        return text[:max_chars].rsplit(" ", 1)[0] + " …"
    return text
