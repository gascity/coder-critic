"""Check recorded workflow ordering and artifact provenance after a real run."""
import argparse
import hashlib
import json
import pathlib
from datetime import datetime

p = argparse.ArgumentParser()
p.add_argument("artifacts", help="directory containing summary.py and reports/")
p.add_argument("beads", help="observer's final beads.json")
a = p.parse_args()
root = pathlib.Path(a.artifacts)
rows = json.loads(pathlib.Path(a.beads).read_text())
steps = {r.get("metadata", {}).get("gc.step_ref"): r for r in rows}
workflow = next(r for r in rows if r.get("metadata", {}).get("gc.kind") == "workflow")
assert workflow["status"] == "closed", "workflow is not closed"
assert workflow["metadata"]["gc.outcome"] == "pass", "workflow did not pass"
names = ["coder-critic.implement", "coder-critic.review", "coder-critic.test", "coder-critic.revise", "coder-critic.verify"]
for name in names:
    assert steps[name]["status"] == "closed", f"{name} is not closed"

def stamp(row, key):
    return datetime.fromisoformat(row[key].replace("Z", "+00:00"))

def follows(child, parent):
    assert stamp(steps[child], "started_at") >= stamp(steps[parent], "closed_at"), f"{child} started before {parent} closed"

follows("coder-critic.review", "coder-critic.implement")
follows("coder-critic.test", "coder-critic.implement")
first_attempt = min((r for r in rows if r.get("metadata", {}).get("gc.control_for") == "revise"), key=lambda r: int(r["metadata"]["gc.attempt"]))
for dependency in ("coder-critic.review", "coder-critic.test"):
    assert stamp(first_attempt, "started_at") >= stamp(steps[dependency], "closed_at"), f"revision started before {dependency} closed"
follows("coder-critic.verify", "coder-critic.revise")
assert steps["coder-critic.revise"]["metadata"]["gc.outcome"] == "pass"

reports = root / "reports"
first = json.loads((reports / "first-tests.json").read_text())
final = json.loads((reports / "final-tests.json").read_text())
control = json.loads((reports / "controller-check.json").read_text())
first_hash = hashlib.sha256((reports / "first-summary.py").read_bytes()).hexdigest()
final_hash = hashlib.sha256((root / "summary.py").read_bytes()).hexdigest()
assert first["code_sha256"] == first_hash
assert first["unchanged_during_test"], "first implementation changed during testing"
assert first_hash in (reports / "review.md").read_text(), "critic did not identify the tested first version"
for name, report in (("controller", control), ("final", final)):
    assert report["exit_code"] == 0, f"{name} tests failed"
    assert report["unchanged_during_test"], f"code changed during {name} tests"
    assert report["code_sha256"] == final_hash, f"{name} tested another revision"
    assert "Ran 12 tests" in report["output"] and "\nOK\n" in report["output"]
assert hashlib.sha256((root / "tests/test_summary.py").read_bytes()).hexdigest() == "6a92781b6bcc709a537a97e7bac900f3806c079b42a0a5e1c20828247e8db0c9", "fixed tests changed"
assert hashlib.sha256((root / "scripts/check.py").read_bytes()).hexdigest() == "520537a5e924ccc1227efc112aba11bcf41f4356551deec6a7c4c5884418e870", "fixed runner changed"
review, test = steps["coder-critic.review"], steps["coder-critic.test"]
overlap = max(stamp(review, "started_at"), stamp(test, "started_at")) < min(stamp(review, "closed_at"), stamp(test, "closed_at"))
print(json.dumps({"workflow_id": workflow["id"], "outcome": "pass", "dependency_order_verified": True, "review_and_test_overlapped": overlap, "first_code_sha256": first_hash, "final_code_sha256": final_hash, "code_changed": first_hash != final_hash, "fixed_tests_unchanged": True, "final_tests": 12}, indent=2))
