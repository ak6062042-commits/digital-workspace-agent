import unittest

from backend.core.privacy import redact_sensitive_text, sanitize_workspace_url
from backend.db.models import StateSnapshot, Task
from backend.tools.os_tool import normalize_app_id


class PrivacyTests(unittest.TestCase):
    def test_common_secret_is_redacted(self):
        self.assertIn("[REDACTED]", redact_sensitive_text("api_key=sk-abcdefghijklmnopqrstuvwxyz"))

    def test_unknown_application_is_rejected(self):
        self.assertIsNone(normalize_app_id("powershell & whoami"))

    def test_workspace_url_removes_credentials_fragments_and_secret_parameters(self):
        url = sanitize_workspace_url("https://user:password@example.com/doc?id=42&token=hidden#section")
        self.assertEqual(url, "https://example.com/doc?id=42")

    def test_invalid_workspace_url_is_rejected(self):
        self.assertIsNone(sanitize_workspace_url("file:///private/document"))

    def test_existing_task_context_is_sanitized_on_output(self):
        task = Task(source_url="https://example.com/work?session=private&view=board", source_title="token=private")
        self.assertEqual(task.to_dict()["source_url"], "https://example.com/work?view=board")
        self.assertEqual(task.to_dict()["source_title"], "[REDACTED]")

    def test_existing_snapshot_is_redacted_on_output(self):
        snapshot = StateSnapshot(active_window_title="password=private", browser_tab_title="token=private")
        self.assertEqual(snapshot.to_dict()["active_window_title"], "[REDACTED]")
        self.assertEqual(snapshot.to_dict()["browser_tab_title"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
