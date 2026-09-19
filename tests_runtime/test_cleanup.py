"""Shutdown must finish successfully, not merely make the process disappear."""
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from run_parallel import stop_supervisor, session_cleanup_errors


class CleanupTests(unittest.TestCase):
    def test_successful_stop_has_budget_for_all_gc_shutdown_phases(self):
        process = Mock(poll=Mock(return_value=None), returncode=0)
        self.assertEqual(stop_supervisor(process), [])
        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=120)
        process.kill.assert_not_called()

    def test_nonzero_exit_is_not_a_clean_shutdown(self):
        process = Mock(poll=Mock(return_value=1), returncode=1)
        self.assertEqual(stop_supervisor(process), ["Owned supervisor exited 1"])
        process.terminate.assert_not_called()

    def test_timeout_fails_even_after_forced_process_cleanup(self):
        process = Mock(poll=Mock(return_value=None), returncode=-9)
        process.wait.side_effect = [subprocess.TimeoutExpired("gc", 120), -9]
        self.assertIn("Owned supervisor required SIGKILL", stop_supervisor(process))
        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_args_list, [call(timeout=120), call(timeout=10)])

    def test_empty_owned_server_is_clean(self):
        with patch("run_parallel.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 0, "", "")):
            self.assertEqual(session_cleanup_errors({}, "demo"), [])

    def test_remaining_worker_is_not_clean(self):
        with patch("run_parallel.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 0, "coder: 1 windows\n", "")):
            self.assertIn("sessions remain", session_cleanup_errors({}, "demo")[0])

    def test_missing_owned_server_is_clean(self):
        with patch("run_parallel.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 1, "", "no server running on /tmp/demo")):
            self.assertEqual(session_cleanup_errors({}, "demo"), [])

    def test_unverifiable_sessions_are_not_clean(self):
        with patch("run_parallel.subprocess.run", return_value=
                   subprocess.CompletedProcess([], 1, "", "permission denied")):
            self.assertIn("Could not verify", session_cleanup_errors({}, "demo")[0])


if __name__ == "__main__":
    unittest.main()
