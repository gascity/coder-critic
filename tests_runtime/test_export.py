"""Keep failed runs and unverified artifacts out of published evidence."""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from export_run import export


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = pathlib.Path(self.tmp.name) / "run"
        self.evidence = self.run / "city/evidence"
        self.evidence.mkdir(parents=True)
        self.destination = pathlib.Path(self.tmp.name) / "published"

    def status(self, **values):
        (self.evidence / "run.json").write_text(json.dumps(values))

    def test_failed_run_cannot_create_export(self):
        self.status(outcome="fail", cleanup_errors=[])
        with self.assertRaisesRegex(RuntimeError, "Refusing to export"):
            export(self.run, self.destination)
        self.assertFalse(self.destination.exists())

    def test_failed_cleanup_cannot_create_export(self):
        self.status(outcome="pass", cleanup_errors=["required SIGKILL"])
        with self.assertRaisesRegex(RuntimeError, "Refusing to export"):
            export(self.run, self.destination)
        self.assertFalse(self.destination.exists())

    def test_changed_fixed_files_cannot_create_export(self):
        self.status(outcome="pass", cleanup_errors=[], database_cleanup={"verified": True})
        (self.evidence / "beads.json").write_text("[]")
        (self.evidence / "fixed-files.json").write_text('{"brief":"before"}')
        with patch("export_run.verify", return_value={}), \
                patch("export_run.fixed_hashes", return_value={"brief": "after"}):
            with self.assertRaisesRegex(RuntimeError, "Fixed run files changed"):
                export(self.run, self.destination)
        self.assertFalse(self.destination.exists())

    def test_missing_database_cleanup_cannot_create_export(self):
        self.status(outcome="pass", cleanup_errors=[])
        with self.assertRaisesRegex(RuntimeError, "verified database cleanup"):
            export(self.run, self.destination)
        self.assertFalse(self.destination.exists())

    def test_running_database_cannot_create_export(self):
        self.status(outcome="pass", cleanup_errors=[], database_cleanup={"verified": True})
        (self.evidence / "beads.json").write_text("[]")
        (self.evidence / "fixed-files.json").write_text("{}")
        with patch("export_run.verify", return_value={}), \
                patch("export_run.fixed_hashes", return_value={}), \
                patch("export_run.owned_ports", return_value={12345}), \
                patch("export_run.port_open", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "Database is running"):
                export(self.run, self.destination)
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
