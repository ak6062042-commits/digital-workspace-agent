import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_AGENT_DIR = ROOT / "system-agent" / "local-agent"


def load_watcher_module():
    sys.path.insert(0, str(LOCAL_AGENT_DIR))
    try:
        spec = importlib.util.spec_from_file_location("workspace_local_watcher", LOCAL_AGENT_DIR / "watcher.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(LOCAL_AGENT_DIR))


class WatcherContractTests(unittest.TestCase):
    def test_snapshot_payload_matches_the_strict_backend_contract(self):
        watcher = load_watcher_module()
        payload = watcher.snapshot_api_payload(
            {
                "active_app": "Browser",
                "active_window_title": "Example",
                "browser_url": "https://example.com",
                "browser_tab_title": "Example",
                "captured_at": "2026-09-28T00:00:00+00:00",
                "metadata": {"hostname": "private-machine"},
            }
        )
        self.assertEqual(set(payload), set(watcher.SNAPSHOT_API_FIELDS))
        self.assertNotIn("metadata", payload)


if __name__ == "__main__":
    unittest.main()
