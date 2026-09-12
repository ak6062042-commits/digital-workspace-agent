import unittest

from backend.core.privacy import redact_sensitive_text
from backend.tools.os_tool import normalize_app_id


class PrivacyTests(unittest.TestCase):
    def test_common_secret_is_redacted(self):
        self.assertIn("[REDACTED]", redact_sensitive_text("api_key=sk-abcdefghijklmnopqrstuvwxyz"))

    def test_unknown_application_is_rejected(self):
        self.assertIsNone(normalize_app_id("powershell & whoami"))


if __name__ == "__main__":
    unittest.main()
