"""Exercise the observer's actual API path without starting agents."""
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from monitor_parallel import observe


class MonitorTests(unittest.TestCase):
    def test_api_observation_then_one_raw_bd_read_for_timestamps(self):
        root = {"id": "root", "status": "closed",
                "metadata": {"gc.kind": "workflow", "gc.outcome": "pass"}}
        raw = [root, {"id": "task", "started_at": "2026-09-19T12:00:00Z",
                      "metadata": {"gc.root_bead_id": "root"}}]
        calls = []
        def api(url, timeout):
            calls.append(url)
            if "/beads?" in url:
                value = {"items": [root], "total": 1}
            else:
                value = {"items": [], "total": 0}
            return io.BytesIO(json.dumps(value).encode())
        command = Mock(return_value=json.dumps(raw))
        with tempfile.TemporaryDirectory() as tmp, \
                patch("monitor_parallel.urllib.request.urlopen", side_effect=api), \
                patch("monitor_parallel.subprocess.run",
                      return_value=subprocess.CompletedProcess([], 0, "off\n", "")):
            evidence = pathlib.Path(tmp)
            result = observe(command, {}, {"port": 12345, "name": "demo"},
                             evidence, "root", 1, Mock(poll=Mock(return_value=None)))
            self.assertEqual(result, raw)
            self.assertEqual(json.loads((evidence / "beads.json").read_text()), raw)
        command.assert_called_once_with(["bd", "list", "--all", "--json", "--limit", "0"])
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(url.startswith("http://127.0.0.1:12345/v0/city/demo/") for url in calls))

    def test_partial_api_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch("monitor_parallel.urllib.request.urlopen",
                      return_value=io.BytesIO(b'{"items":[],"partial":true}')):
            with self.assertRaisesRegex(RuntimeError, "Incomplete API observation"):
                observe(Mock(), {}, {"port": 12345, "name": "demo"},
                        pathlib.Path(tmp), "root", 1, Mock(poll=Mock(return_value=None)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
