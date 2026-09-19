"""Bounded fixed checks; every run records its source hashes and actual output."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = ("records.py", "totals.py", "summary.py")


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in FILES if (ROOT / name).exists()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("part", choices=("parse", "aggregate", "all"))
    p.add_argument("--controller", action="store_true")
    a = p.parse_args()
    if a.controller and a.part != "all":
        p.error("The controller checks the complete artifact")
    specs = {"parse": [("tests_parts", "test_records.py", 6)],
             "aggregate": [("tests_parts", "test_totals.py", 6)],
             "all": [("tests_parts", "test_*.py", 12), ("tests", "test_summary.py", 12)]}[a.part]
    before = hashes()
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "part": a.part, "source_sha256": before, "checks": []}
    code = 0
    for directory, pattern, count in specs:
        try:
            run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", directory, "-p", pattern, "-v"], cwd=ROOT, capture_output=True, text=True, timeout=20)
            output = run.stdout + run.stderr
            passed = run.returncode == 0 and f"Ran {count} tests" in output and "\nOK\n" in output
            report["checks"].append({"suite": directory, "exit_code": run.returncode, "passed": passed, "output": output})
        except subprocess.TimeoutExpired:
            passed = False
            report["checks"].append({"suite": directory, "passed": False, "error": "20-second test timeout"})
        if not passed:
            code = 1
    relevant = {"parse": ["records.py"], "aggregate": ["totals.py"], "all": list(FILES)}[a.part]
    after = hashes()
    report["unchanged_during_test"] = all(before.get(f) == after.get(f) and f in before for f in relevant)
    if not report["unchanged_during_test"]:
        code = 1
    report.update(finished_at=datetime.now(timezone.utc).isoformat(), exit_code=code)
    (ROOT / "reports").mkdir(exist_ok=True)
    filename = "controller-tests.json" if a.controller else f"{a.part}-tests.json"
    (ROOT / "reports" / filename).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
