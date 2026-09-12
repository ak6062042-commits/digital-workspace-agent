"""Privacy minimisation and lightweight local secret redaction."""
from __future__ import annotations

import re


_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
)


def redact_sensitive_text(value: str, limit: int = 2000) -> str:
    """Redact common credential/PII patterns and enforce a storage cap."""
    result = (value or "").strip()[:limit]
    for pattern in _PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def safe_excerpt(value: str, limit: int = 300) -> str:
    return redact_sensitive_text(value, limit=limit)
