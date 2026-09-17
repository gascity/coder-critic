"""Observe a demo workflow without claiming or completing any work."""
import argparse
import json
import pathlib
import subprocess
import time
from datetime import datetime, timezone

p = argparse.ArgumentParser()
p.add_argument("city")
p.add_argument("workflow")
p.add_argument("--minutes", type=float, default=20)
p.add_argument("--output", required=True)
a = p.parse_args()
out = pathlib.Path(a.output)
out.mkdir(parents=True, exist_ok=True)
deadline = time.monotonic() + a.minutes * 60
while time.monotonic() < deadline:
    run = subprocess.run(["gc", "--city", a.city, "bd", "list", "--all", "--json", "--limit", "0"], capture_output=True, text=True, timeout=60)
    if run.returncode:
        raise RuntimeError(run.stderr)
    rows = json.loads(run.stdout)
    rows = [r for r in rows if r["id"] == a.workflow or r.get("metadata", {}).get("gc.root_bead_id") == a.workflow]
    stamp = datetime.now(timezone.utc).isoformat()
    with (out / "timeline.jsonl").open("a") as f:
        f.write(json.dumps({"observed_at": stamp, "beads": rows}) + "\n")
    (out / "beads.json").write_text(json.dumps(rows, indent=2) + "\n")
    tasks = [r for r in rows if r["id"] != a.workflow and not r.get("metadata", {}).get("gc.kind")]
    print(stamp, " | ".join(f'{r.get("metadata", {}).get("gc.step_ref", r["id"])}={r["status"]}' for r in tasks), flush=True)
    root = next(r for r in rows if r["id"] == a.workflow)
    if root["status"] == "closed":
        print("Workflow closed:", json.dumps(root), flush=True)
        raise SystemExit(0 if root.get("metadata", {}).get("gc.outcome") == "pass" else 2)
    time.sleep(15)
raise SystemExit("Observation deadline reached; workflow completion not established")
