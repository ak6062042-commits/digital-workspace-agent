"""Live web-search helpers used by the personal research workflow."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger("SearchTool")
_SEARCH_URL = "https://html.duckduckgo.com/html/"
_EXA_SEARCH_URL = "https://api.exa.ai/search"
_USER_AGENT = "DigitalWorkspaceAgent/2.1 (+local personal research)"


def _clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def _destination_url(href: str | None) -> str | None:
    if not href:
        return None
    parsed = urlparse(href)
    if not parsed.scheme and href.startswith("//"):
        parsed = urlparse(f"https:{href}")
    elif not parsed.scheme and href.startswith("/"):
        parsed = urlparse(f"https://duckduckgo.com{href}")
    if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.startswith("/l/"):
        destination = parse_qs(parsed.query).get("uddg", [None])[0]
        if destination:
            href = unquote(destination)
            parsed = urlparse(href)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed.geturl()


def _result_record(title: str, url: str, snippet: str) -> dict[str, str]:
    parsed = urlparse(url)
    return {
        "title": _clean_text(title)[:300] or parsed.netloc,
        "url": url,
        "snippet": _clean_text(snippet)[:900],
        "domain": parsed.netloc.removeprefix("www."),
    }


def _html_results(html: str, maximum: int) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for link in soup.select("a.result__a, a[data-testid='result-title-a']"):
        url = _destination_url(link.get("href"))
        if not url or url in seen_urls:
            continue
        container = link.find_parent(class_=lambda classes: classes and "result" in classes)
        snippet_node = container.select_one(".result__snippet, [data-result='snippet']") if container else None
        results.append(_result_record(link.get_text(" ", strip=True), url, snippet_node.get_text(" ", strip=True) if snippet_node else ""))
        seen_urls.add(url)
        if len(results) >= maximum:
            return results
    return results


def _instant_answer_results(query: str, maximum: int) -> list[dict[str, str]]:
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=6.0,
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.info("DuckDuckGo instant-answer fallback failed: %s", error)
        return []

    results: list[dict[str, str]] = []
    if data.get("AbstractURL"):
        results.append(_result_record(data.get("Heading") or query, data["AbstractURL"], data.get("Abstract") or ""))
    for topic in data.get("RelatedTopics", []):
        if not isinstance(topic, dict):
            continue
        if topic.get("FirstURL") and topic.get("Text"):
            results.append(_result_record(topic["Text"], topic["FirstURL"], topic["Text"]))
        if len(results) >= maximum:
            break
    return results


def _bing_rss_results(query: str, maximum: int) -> list[dict[str, str]]:
    """Use Bing's RSS representation when DuckDuckGo serves a challenge page."""
    try:
        response = requests.get(
            "https://www.bing.com/search",
            params={"format": "rss", "q": query},
            timeout=8.0,
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
    except (requests.RequestException, ElementTree.ParseError) as error:
        logger.info("Bing RSS search fallback failed: %s", error)
        return []

    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in root.findall(".//item"):
        url = _destination_url(item.findtext("link"))
        if not url or url in seen_urls:
            continue
        title = BeautifulSoup(item.findtext("title") or "", "html.parser").get_text(" ", strip=True)
        snippet = BeautifulSoup(item.findtext("description") or "", "html.parser").get_text(" ", strip=True)
        results.append(_result_record(title, url, snippet))
        seen_urls.add(url)
        if len(results) >= maximum:
            break
    return results


def search_exa(query: str, api_key: str, max_results: int = 6, max_characters: int = 6000) -> list[dict[str, str]]:
    """Return Exa results, including its extracted text when the API supplies it."""
    clean_query = _clean_text(query)
    if not clean_query or not api_key:
        return []
    maximum = max(1, min(max_results, 10))
    character_limit = max(500, min(max_characters, 12000))
    try:
        response = requests.post(
            _EXA_SEARCH_URL,
            json={
                "query": clean_query,
                "type": "auto",
                "numResults": maximum,
                "contents": {"text": {"maxCharacters": character_limit}},
            },
            timeout=12.0,
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.info("Exa search unavailable; using local fallback: %s", error)
        return []

    raw_results = payload.get("results", [])
    if not isinstance(raw_results, list):
        logger.info("Exa search returned an unexpected response shape")
        return []

    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        url = _destination_url(str(item.get("url") or ""))
        if not url or url in seen_urls:
            continue
        highlights = item.get("highlights")
        highlight_text = " ".join(str(value) for value in highlights if isinstance(value, str)) if isinstance(highlights, list) else ""
        content = _clean_text(str(item.get("text") or item.get("summary") or highlight_text))[:character_limit]
        record = _result_record(str(item.get("title") or urlparse(url).netloc), url, content)
        record["content"] = content
        record["provider"] = "exa"
        results.append(record)
        seen_urls.add(url)
        if len(results) >= maximum:
            break
    return results


def search_web(query: str, max_results: int = 6) -> list[dict[str, str]]:
    """Return live, deduplicated search results with title, URL, snippet, and domain."""
    clean_query = _clean_text(query)
    if not clean_query:
        return []
    maximum = max(1, min(max_results, 10))
    try:
        response = requests.get(
            _SEARCH_URL,
            params={"q": clean_query},
            timeout=8.0,
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()
        results = _html_results(response.text, maximum)
        if results:
            return results
    except requests.RequestException as error:
        logger.info("Live DuckDuckGo HTML search failed: %s", error)

    bing_results = _bing_rss_results(clean_query, maximum)
    if bing_results:
        return bing_results

    instant_results = _instant_answer_results(clean_query, maximum)
    if instant_results:
        return instant_results
    return [
        _result_record(
            f"Search results for {clean_query}",
            f"https://duckduckgo.com/?q={quote(clean_query)}",
            "Live search could not be reached from this machine. Open the query in your browser and retry when connectivity is available.",
        )
    ]
