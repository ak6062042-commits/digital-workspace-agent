"""Create or repair the local .env without printing its secret token."""
from __future__ import annotations

import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"
PLACEHOLDERS = {"", "replace-with-a-long-random-token", "change-me"}


def parse(lines: list[str]) -> dict[str, str]:
    values = {}
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def main() -> None:
    template_lines = EXAMPLE.read_text(encoding="utf-8").splitlines()
    current_lines = TARGET.read_text(encoding="utf-8").splitlines() if TARGET.exists() else template_lines
    values = parse(current_lines)
    token = values.get("API_TOKEN", "")
    if token in PLACEHOLDERS:
        token = secrets.token_urlsafe(32)
    values["API_TOKEN"] = token
    values["VITE_API_TOKEN"] = token
    # The previous MVP default exposed the backend on every interface. Migrate it safely.
    if values.get("BACKEND_HOST", "") in {"", "0.0.0.0"}:
        values["BACKEND_HOST"] = "127.0.0.1"
    # Chrome is the supported visible search provider. Migrate the former
    # default so an existing setup follows the current privacy/UX contract.
    if values.get("WEB_SEARCH_PROVIDER", "").strip().lower() in {"", "duckduckgo"}:
        values["WEB_SEARCH_PROVIDER"] = "chrome"
    output = []
    seen = set()
    for line in template_lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            output.append(f"{key}={values.get(key, line.split('=', 1)[1])}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in seen:
            output.append(f"{key}={value}")
    TARGET.write_text("\n".join(output) + "\n", encoding="utf-8")
    print("Local configuration is ready. API_TOKEN was generated or preserved without printing it.")


if __name__ == "__main__":
    main()
