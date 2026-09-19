"""An unverified provider must fail before coding workers start."""
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from runtime_common import require_claude_auth


class AuthTests(unittest.TestCase):
    def test_authenticated_provider(self):
        with patch("runtime_common.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 0, '{"loggedIn":true}', '')) as run:
            require_claude_auth({"DISABLE_AUTOUPDATER": "1"})
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

    def test_signed_out_provider(self):
        with patch("runtime_common.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 0, '{"loggedIn":false}', '')):
            with self.assertRaisesRegex(RuntimeError, "Authenticate Claude"):
                require_claude_auth({})

    def test_unverifiable_provider(self):
        with patch("runtime_common.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 1, '', 'private diagnostic')):
            with self.assertRaisesRegex(RuntimeError, "Could not verify Claude"):
                require_claude_auth({})

    def test_probe_timeout_is_not_ignored(self):
        with patch("runtime_common.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("claude", 30)):
            with self.assertRaisesRegex(RuntimeError, "30 seconds"):
                require_claude_auth({})
