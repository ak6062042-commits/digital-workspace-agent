"""Single, deliberately small runtime configuration layer."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    """Load simple KEY=VALUE entries without overriding process environment."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./backend/db/app.db")
    backend_host: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    api_token: str = os.getenv("API_TOKEN", "")
    cors_origin: str = os.getenv("CORS_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173")
    request_max_bytes: int = int(os.getenv("REQUEST_MAX_BYTES", "65536"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    snapshot_retention_days: int = int(os.getenv("SNAPSHOT_RETENTION_DAYS", "14"))
    content_retention_days: int = int(os.getenv("CONTENT_RETENTION_DAYS", "30"))
    capture_enabled: bool = _bool("CAPTURE_ENABLED", False)
    allow_external_llm: bool = _bool("ALLOW_EXTERNAL_LLM", False)
    auto_execute_low_risk: bool = _bool("AUTO_EXECUTE_LOW_RISK", True)
    allow_container_bind: bool = _bool("ALLOW_CONTAINER_BIND", False)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origin.split(",") if origin.strip()]

    def validate_runtime(self) -> None:
        insecure_token = not self.api_token or self.api_token in {"change-me", "replace-with-a-long-random-token"}
        if insecure_token:
            raise RuntimeError("API_TOKEN must be a long random value. Run scripts/setup before starting the backend.")
        if self.backend_host not in {"127.0.0.1", "localhost", "::1"} and not (self.backend_host == "0.0.0.0" and self.allow_container_bind):
            raise RuntimeError("BACKEND_HOST must remain loopback; use an authenticated reverse proxy for remote access.")


settings = Settings()
