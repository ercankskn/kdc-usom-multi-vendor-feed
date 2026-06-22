import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate-firewall-config.py"


class FirewallGeneratorTests(unittest.TestCase):
    def test_all_vendor_aliases_generate(self):
        for alias in ("pa", "fg", "sf", "cp", "sw", "wg"):
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as temp_dir:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--vendor",
                        alias,
                        "--base-url",
                        "https://feed.example.com:8443",
                        "--output",
                        temp_dir,
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                manifests = list(Path(temp_dir).glob("*/manifest.json"))
                self.assertEqual(len(manifests), 1)
                data = json.loads(manifests[0].read_text(encoding="utf-8"))
                self.assertFalse(data["safety"]["automatic_firewall_changes"])
                self.assertTrue(data["base_url"].startswith("https://"))

    def test_http_rejected_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--vendor",
                    "fg",
                    "--base-url",
                    "http://feed.example.com",
                    "--output",
                    temp_dir,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("plain HTTP is disabled", result.stderr)


if __name__ == "__main__":
    unittest.main()
