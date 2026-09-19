"""Read-only observation of Beads, Gas City sessions and the tmux server."""
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone


def observe(command, env, manifest, evidence, workflow, minutes, supervisor):
    deadline = time.monotonic() + minutes * 60
    server_seen = False
    base = f"http://127.0.0.1:{manifest['port']}/v0/city/{manifest['name']}"
    def read(path):
        with urllib.request.urlopen(base + path, timeout=30) as response:
            result = json.load(response)
        if result.get("partial") or result.get("next_cursor"):
            raise RuntimeError("Incomplete API observation; refusing partial evidence")
        return result
    while time.monotonic() < deadline:
        if supervisor.poll() is not None:
            raise RuntimeError("Owned supervisor exited during the workflow")
        all_rows = read("/beads?all=true&limit=100")["items"]
        rows = [r for r in all_rows if r["id"] == workflow or r.get("metadata", {}).get("gc.root_bead_id") == workflow]
        root = next(r for r in rows if r["id"] == workflow)
        ready = read("/beads/ready")["items"]
        sessions = read("/sessions")
        runtime = subprocess.run(["tmux", "-L", manifest["name"], "show-options", "-sv", "exit-empty"], env=env, capture_output=True, text=True, timeout=10)
        observation = {"observed_at": datetime.now(timezone.utc).isoformat(), "beads": rows, "ready": ready, "sessions": sessions, "tmux_alive": runtime.returncode == 0, "tmux_exit_empty": runtime.stdout.strip()}
        with (evidence / "timeline.jsonl").open("a") as stream:
            stream.write(json.dumps(observation) + "\n")
        (evidence / "beads.json").write_text(json.dumps(rows, indent=2) + "\n")
        tasks = [r for r in rows if not r.get("metadata", {}).get("gc.kind")]
        print(observation["observed_at"], " | ".join(f'{r.get("metadata", {}).get("gc.step_ref", r["id"])}={r["status"]}' for r in tasks), flush=True)
        if root["status"] == "closed":
            if root.get("metadata", {}).get("gc.outcome") != "pass":
                raise RuntimeError("Workflow closed without passing")
            # API projections omit bd's start/close timestamps. Read the raw
            # backing record once, after completion, for the overlap proof.
            raw = json.loads(command(["bd", "list", "--all", "--json", "--limit", "0"]))
            rows = [r for r in raw if r["id"] == workflow or r.get("metadata", {}).get("gc.root_bead_id") == workflow]
            (evidence / "beads.json").write_text(json.dumps(rows, indent=2) + "\n")
            return rows
        if server_seen and runtime.returncode:
            raise RuntimeError("tmux server disappeared; no recovery attempted")
        if runtime.returncode == 0:
            server_seen = True
            if runtime.stdout.strip() not in ("off", "0"):
                raise RuntimeError("tmux exit-empty must be off during worker turnover")
            windows = subprocess.run(["tmux", "-L", manifest["name"], "list-panes", "-a", "-F", "#{pane_id}"], env=env, capture_output=True, text=True, timeout=10)
            for pane in windows.stdout.splitlines():
                screen = subprocess.run(["tmux", "-L", manifest["name"], "capture-pane", "-p", "-t", pane], env=env, capture_output=True, text=True, timeout=10).stdout
                if "This command requires approval" in screen or "Do you want to proceed?" in screen:
                    (evidence / "blocked-approval.txt").write_text(screen)
                    raise RuntimeError("Worker blocked on approval; no approval or rescue attempted")
        time.sleep(10)
    raise TimeoutError("Workflow deadline reached; run failed, not silently extended")
