"""Reproduce a database restart after supervisor exit without real processes."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from cleanup_database import cleanup_database


class DatabaseCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.city = pathlib.Path(self.tmp.name).resolve()
        self.state = self.city / ".gc/runtime/packs/dolt/dolt-state.json"
        self.state.parent.mkdir(parents=True)
        self.state.write_text(json.dumps({"port": 12345, "data_dir": str(self.city / ".beads/dolt")}))
        self.now = 0
        def sleep(seconds):
            self.now += seconds
        self.clock = patch("cleanup_database.time.monotonic", side_effect=lambda: self.now)
        self.sleep = patch("cleanup_database.time.sleep", side_effect=sleep)
        self.clock.start()
        self.sleep.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.sleep.stop)

    def test_already_stopped_waits_for_quiet_period(self):
        with patch("cleanup_database.port_open", return_value=False), \
                patch("cleanup_database.subprocess.run") as stop:
            report = cleanup_database(self.city, {})
        self.assertTrue(report["verified"])
        self.assertEqual(self.now, 15)
        stop.assert_not_called()

    def test_retained_provider_state_supplies_port_after_clean_stop(self):
        self.state.rename(self.state.with_name("dolt-provider-state.json"))
        with patch("cleanup_database.port_open", return_value=False) as probe:
            report = cleanup_database(self.city, {})
        self.assertEqual(report["ports"], [12345])
        probe.assert_called_with(12345)

    def test_missing_endpoint_cannot_pass_vacuously(self):
        self.state.unlink()
        with self.assertRaisesRegex(RuntimeError, "No owned database endpoint"):
            cleanup_database(self.city, {})

    def test_late_restart_is_stopped_then_quiet_period_restarts(self):
        with patch("cleanup_database.port_open", side_effect=lambda port: self.now == 6), \
                patch("cleanup_database.subprocess.run", return_value=
                      subprocess.CompletedProcess([], 0, "", "")) as stop:
            report = cleanup_database(self.city, {})
        self.assertTrue(report["verified"])
        self.assertEqual(report["stop_attempts"], 1)
        self.assertEqual(self.now, 22)
        self.assertEqual(stop.call_args.args[0], ["gc", "dolt-state", "stop-managed",
                         "--city", str(self.city), "--port", "12345"])

    def test_foreign_data_directory_is_rejected_before_any_stop(self):
        self.state.write_text(json.dumps({"port": 12345, "data_dir": "/unrelated/data"}))
        with patch("cleanup_database.subprocess.run") as stop:
            with self.assertRaisesRegex(RuntimeError, "does not belong"):
                cleanup_database(self.city, {})
        stop.assert_not_called()

    def test_stop_failure_is_not_ignored(self):
        with patch("cleanup_database.port_open", return_value=True), \
                patch("cleanup_database.subprocess.run", return_value=
                      subprocess.CompletedProcess([], 1, "", "lock held")):
            with self.assertRaisesRegex(RuntimeError, "database stop failed"):
                cleanup_database(self.city, {})

    def test_listener_that_never_stops_fails_by_deadline(self):
        with patch("cleanup_database.port_open", return_value=True), \
                patch("cleanup_database.subprocess.run", return_value=
                      subprocess.CompletedProcess([], 0, "", "")):
            with self.assertRaisesRegex(TimeoutError, "did not stay stopped"):
                cleanup_database(self.city, {}, timeout=4)
        self.assertEqual(self.now, 4)
