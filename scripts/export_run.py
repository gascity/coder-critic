"""Publish a compact, replayable record only after a verified unattended run."""
import argparse
import json
import pathlib
import shutil
from datetime import datetime, timezone
from cleanup_database import owned_ports, port_open
from verify_parallel import verify
from run_parallel import fixed_hashes


def export(run, destination):
    city = run / "city"
    evidence = city / "evidence"
    status = json.loads((evidence / "run.json").read_text())
    if status.get("outcome") != "pass" or status.get("cleanup_errors"):
        raise RuntimeError("Refusing to export a failed or incompletely cleaned-up run")
    if not status.get("database_cleanup", {}).get("verified"):
        raise RuntimeError("Refusing to export without verified database cleanup")
    rows = json.loads((evidence / "beads.json").read_text())
    proof = verify(city, rows)
    baseline = json.loads((evidence / "fixed-files.json").read_text())
    if baseline != fixed_hashes(city):
        raise RuntimeError("Fixed run files changed after verification")
    ports = owned_ports(city)
    if not ports or any(port_open(port) for port in ports):
        raise RuntimeError("Database is running or its endpoint cannot be verified; refusing export")
    destination.mkdir(parents=True, exist_ok=False)
    for name in ("records.py", "totals.py", "summary.py", "BRIEF.md"):
        shutil.copy2(city / name, destination / name)
    for name in ("reports", "tests", "tests_parts"):
        shutil.copytree(city / name, destination / name,
                        ignore=shutil.ignore_patterns("__pycache__"))
    output = destination / "evidence"
    output.mkdir()
    for name in ("run.json", "beads.json", "fixed-files.json", "verification.json"):
        shutil.copy2(evidence / name, output / name)
    (output / "database-check.json").write_text(json.dumps({
        "verified": True, "ports": sorted(ports),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "check": "Independent read-only TCP check of retained owned database endpoints",
    }, indent=2) + "\n")
    # Preserve state transitions and ready-work IDs, not full session commands,
    # internal holder tokens, or other runtime implementation details.
    ids = {row["id"] for row in rows}
    transitions = []
    previous = None
    for line in (evidence / "timeline.jsonl").read_text().splitlines():
        frame = json.loads(line)
        state = {
            "steps": [{key: row.get(key) for key in ("id", "status", "assignee")}
                      for row in frame["beads"]],
            "ready_ids": sorted(row["id"] for row in frame["ready"] if row["id"] in ids),
            "tmux_alive": frame["tmux_alive"],
        }
        if state != previous:
            transitions.append({"observed_at": frame["observed_at"], **state})
            previous = state
    (output / "transitions.json").write_text(json.dumps(transitions, indent=2) + "\n")
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("destination", type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(export(args.run.resolve(), args.destination.resolve()), indent=2))
