"""Privacy minimisation and lightweight local secret redaction."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
)

_SENSITIVE_QUERY_KEYS = {
    "access_token", "apikey", "api_key", "auth", "authorization", "code",
    "key", "password", "secret", "session", "sig", "signature", "state", "token",
}


def redact_sensitive_text(value: str, limit: int = 2000) -> str:
    """Redact common credential/PII patterns and enforce a storage cap."""
    result = (value or "").strip()[:limit]
    for pattern in _PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def safe_excerpt(value: str, limit: int = 300) -> str:
    return redact_sensitive_text(value, limit=limit)


def sanitize_workspace_url(value: str | None, limit: int = 1000) -> str | None:
    """Keep useful web context while excluding credentials and secret-bearing URL parts."""
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        host = parsed.hostname.lower()
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        netloc = host if parsed.port is None else f"{host}:{parsed.port}"
        query = urlencode(
            [(key, item) for key, item in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() not in _SENSITIVE_QUERY_KEYS],
            doseq=True,
        )
        return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", query, ""))[:limit]
    except (TypeError, ValueError):
        return None
