"""Fail unless different workers overlapped and integration waited for both."""
import argparse
import hashlib
import json
import pathlib
from datetime import datetime


def verify(city, rows):
    steps = {r.get("metadata", {}).get("gc.step_ref"): r for r in rows}
    workflow = next(r for r in rows if r.get("metadata", {}).get("gc.kind") == "workflow")
    assert workflow["status"] == "closed" and workflow["metadata"].get("gc.outcome") == "pass", "workflow did not pass"
    parse, aggregate = (steps[f"parallel-summary.{name}"] for name in ("parse", "aggregate"))
    def stamp(row, key):
        return datetime.fromisoformat(row[key].replace("Z", "+00:00"))
    for row in (parse, aggregate):
        assert row["status"] == "closed", "implementation not complete"
        assert row.get("assignee"), "missing worker identity"
    assert parse["assignee"] != aggregate["assignee"], "implementations were not claimed by different workers"
    assert max(stamp(r, "started_at") for r in (parse, aggregate)) < min(stamp(r, "closed_at") for r in (parse, aggregate)), "coding tasks did not overlap"
    attempts = [r for r in rows if r.get("metadata", {}).get("gc.control_for") == "integrate"]
    assert attempts, "missing integration attempt"
    for attempt in attempts:
        for prerequisite in (parse, aggregate):
            assert stamp(attempt, "started_at") >= stamp(prerequisite, "closed_at"), "integration started before both prerequisites closed"
    integration = steps["parallel-summary.integrate"]
    assert integration["status"] == "closed" and integration["metadata"].get("gc.outcome") == "pass", "controller did not pass integration"
    report = json.loads((city / "reports/all-tests.json").read_text())
    assert report["exit_code"] == 0 and report["unchanged_during_test"], "final checks failed or code changed while testing"
    for name in ("records.py", "totals.py", "summary.py"):
        assert report["source_sha256"][name] == hashlib.sha256((city / name).read_bytes()).hexdigest(), f"wrong tested version: {name}"
    assert len(report["checks"]) == 2 and all(c["passed"] for c in report["checks"]), "missing acceptance checks"
    controller = json.loads((city / "reports/controller-tests.json").read_text())
    assert controller["exit_code"] == 0 and controller["unchanged_during_test"], "controller checks failed"
    assert controller["source_sha256"] == report["source_sha256"], "controller checked a different artifact"
    return {"workflow_id": workflow["id"], "outcome": "pass", "different_coding_workers": True, "coding_tasks_overlapped": True, "integration_waited_for_both": True, "integration_attempts": len(attempts), "source_sha256": report["source_sha256"], "tests": 24}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("city", type=pathlib.Path)
    p.add_argument("beads", type=pathlib.Path)
    a = p.parse_args()
    print(json.dumps(verify(a.city, json.loads(a.beads.read_text())), indent=2))
