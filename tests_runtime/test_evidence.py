"""Red-capable verifier checks; these are not substitutes for real agent runs."""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from verify_parallel import verify


def stamp(second):
    return f"2026-09-19T12:00:{second:02d}Z"


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.city = pathlib.Path(self.tmp.name)
        (self.city / "reports").mkdir()
        hashes = {}
        for name in ("records.py", "totals.py", "summary.py"):
            (self.city / name).write_text("# fixture\n")
            hashes[name] = hashlib.sha256(b"# fixture\n").hexdigest()
        report = {"exit_code": 0, "unchanged_during_test": True, "source_sha256": hashes, "checks": [{"passed": True}, {"passed": True}]}
        (self.city / "reports/all-tests.json").write_text(json.dumps(report))
        (self.city / "reports/controller-tests.json").write_text(json.dumps(report))
        self.rows = [
            {"id": "root", "status": "closed", "metadata": {"gc.kind": "workflow", "gc.outcome": "pass"}},
            {"status": "closed", "assignee": "coder-1", "started_at": stamp(1), "closed_at": stamp(10), "metadata": {"gc.step_ref": "parallel-summary.parse"}},
            {"status": "closed", "assignee": "coder-2", "started_at": stamp(2), "closed_at": stamp(12), "metadata": {"gc.step_ref": "parallel-summary.aggregate"}},
            {"started_at": stamp(13), "metadata": {"gc.control_for": "integrate"}},
            {"status": "closed", "metadata": {"gc.step_ref": "parallel-summary.integrate", "gc.outcome": "pass"}},
        ]

    def test_accept_valid_record(self):
        self.assertTrue(verify(self.city, self.rows)["coding_tasks_overlapped"])

    def test_reject_sequential_work(self):
        self.rows[2]["started_at"] = stamp(11)
        with self.assertRaisesRegex(AssertionError, "did not overlap"):
            verify(self.city, self.rows)

    def test_reject_one_worker(self):
        self.rows[2]["assignee"] = "coder-1"
        with self.assertRaisesRegex(AssertionError, "different workers"):
            verify(self.city, self.rows)

    def test_reject_early_integration(self):
        self.rows[3]["started_at"] = stamp(9)
        with self.assertRaisesRegex(AssertionError, "before both"):
            verify(self.city, self.rows)

    def test_reject_changed_code(self):
        (self.city / "summary.py").write_text("# changed after tests\n")
        with self.assertRaisesRegex(AssertionError, "wrong tested version"):
            verify(self.city, self.rows)

    def test_reject_failed_workflow(self):
        self.rows[0]["metadata"]["gc.outcome"] = "fail"
        with self.assertRaisesRegex(AssertionError, "workflow did not pass"):
            verify(self.city, self.rows)
