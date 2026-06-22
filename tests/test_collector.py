import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "collector.py"
spec = importlib.util.spec_from_file_location("collector", MODULE_PATH)
collector = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(collector)


class NormalizationTests(unittest.TestCase):
    def test_domain(self):
        self.assertEqual(collector.normalize_domain("EXAMPLE.COM."), "example.com")

    def test_ipv4(self):
        self.assertEqual(collector.normalize_ip("192.0.2.10", "ip"), "192.0.2.10")
        self.assertIsNone(collector.normalize_ip("2001:db8::1", "ip"))

    def test_url(self):
        self.assertEqual(
            collector.normalize_url("https://Example.COM/a?b=1"),
            "example.com/a?b=1",
        )

    def test_route_config_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "routes.json"
            path.write_text(
                json.dumps({"status_prefix": "core", "outputs": {"../x": "domain"}}),
                encoding="utf-8",
            )
            original = collector.ROUTE_CONFIG
            collector.ROUTE_CONFIG = path
            try:
                with self.assertRaises(RuntimeError):
                    collector.load_route_config()
            finally:
                collector.ROUTE_CONFIG = original


if __name__ == "__main__":
    unittest.main()
