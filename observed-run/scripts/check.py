"""Run the fixed acceptance suite and record exactly which code was tested."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--record", required=True)
args = parser.parse_args()
code = ROOT / "summary.py"
started = datetime.now(timezone.utc).isoformat()
before = hashlib.sha256(code.read_bytes()).hexdigest() if code.exists() else None
run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, capture_output=True, text=True)
after = hashlib.sha256(code.read_bytes()).hexdigest() if code.exists() else None
record = {"started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(), "code_sha256": before, "unchanged_during_test": before == after, "exit_code": run.returncode, "output": run.stdout + run.stderr}
target = ROOT / args.record
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2), flush=True)
sys.exit(run.returncode if before == after else 2)
