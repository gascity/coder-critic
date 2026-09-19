import os
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from runtime_common import available_port, isolated_env


class IsolationTests(unittest.TestCase):
    def test_external_endpoint_and_session_cannot_leak_in(self):
        with patch.dict(os.environ, {"GC_DOLT_HOST": "production", "BEADS_DIR": "/other", "BD_ALLOW_REMOTE_MIGRATE": "1", "TMUX": "other", "GC_SUPERVISOR_SYSTEMD_UNIT": "real.service"}):
            env = isolated_env("/tmp/example-test")
        for key in ("GC_DOLT_HOST", "BEADS_DIR", "BD_ALLOW_REMOTE_MIGRATE", "TMUX", "GC_SUPERVISOR_SYSTEMD_UNIT"):
            self.assertNotIn(key, env)
        self.assertEqual(env["GC_HOME"], str(pathlib.Path("/tmp/example-test").resolve() / "home"))
        self.assertEqual(env["HOME"], os.environ["HOME"])

    def test_own_api_port(self):
        port = available_port()
        self.assertGreater(port, 1024)
        self.assertNotEqual(port, 8372)
