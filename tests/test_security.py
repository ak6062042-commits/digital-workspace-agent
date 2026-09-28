import unittest
import asyncio

from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.core.config import Settings
from backend.main import SnapshotCreateRequest, _clean_snapshot


class RuntimeSecurityTests(unittest.TestCase):
    def test_loopback_configuration_with_long_token_is_accepted(self):
        settings = Settings(api_token="a" * 32)
        settings.validate_runtime()

    def test_short_token_is_rejected(self):
        with self.assertRaises(RuntimeError):
            Settings(api_token="short").validate_runtime()

    def test_wildcard_cors_is_rejected(self):
        with self.assertRaises(RuntimeError):
            Settings(api_token="a" * 32, cors_origin="*").validate_runtime()

    def test_external_cors_origin_is_rejected_for_loopback_service(self):
        with self.assertRaises(RuntimeError):
            Settings(api_token="a" * 32, cors_origin="https://example.com").validate_runtime()

    def test_snapshot_rejects_undeclared_metadata(self):
        with self.assertRaises(ValidationError):
            SnapshotCreateRequest.model_validate({"active_app": "Browser", "metadata": {"source": "unknown"}})

    def test_snapshot_storage_minimizes_sensitive_workspace_context(self):
        values = _clean_snapshot(
            SnapshotCreateRequest(
                active_window_title="token=private",
                browser_url="https://example.com/doc?id=42&token=private#section",
                browser_tab_title="password=private",
            )
        )
        self.assertEqual(values["browser_url"], "https://example.com/doc?id=42")
        self.assertEqual(values["active_window_title"], "[REDACTED]")
        self.assertEqual(values["browser_tab_title"], "[REDACTED]")

    def test_trusted_host_middleware_rejects_an_unknown_host(self):
        async def endpoint(_scope, _receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        async def request(host: str) -> int:
            messages = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            middleware = TrustedHostMiddleware(endpoint, allowed_hosts=["localhost", "127.0.0.1"])
            await middleware(
                {"type": "http", "method": "GET", "path": "/health", "headers": [(b"host", host.encode())]},
                receive,
                send,
            )
            return messages[0]["status"]

        self.assertEqual(asyncio.run(request("localhost:8000")), 200)
        self.assertEqual(asyncio.run(request("attacker.invalid")), 400)


if __name__ == "__main__":
    unittest.main()
