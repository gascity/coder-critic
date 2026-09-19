"""Own one isolated supervisor; launch, observe, verify, and clean up a real run."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from runtime_common import isolated_env, require_claude_auth
from monitor_parallel import observe
from verify_parallel import verify
from cleanup_database import cleanup_database


def fixed_hashes(city):
    paths = [city / "BRIEF.md", city / "city.toml", city / "pack.toml"]
    for directory in ("tests", "tests_parts", "scripts", "agents", "formulas"):
        paths.extend(p for p in (city / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return {str(p.relative_to(city)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def stop_supervisor(supervisor):
    errors = []
    if supervisor.poll() is None:
        supervisor.terminate()
        try:
            # GC 1.4.1 has separate city, worker-wave, forced-wait and
            # provider-stop phases. Give the whole sequence a fixed budget.
            supervisor.wait(timeout=120)
        except subprocess.TimeoutExpired:
            supervisor.kill()
            supervisor.wait(timeout=10)
            errors.append("Owned supervisor required SIGKILL")
    if supervisor.returncode != 0:
        errors.append(f"Owned supervisor exited {supervisor.returncode}")
    return errors


def session_cleanup_errors(env, name):
    result = subprocess.run(["tmux", "-L", name, "list-sessions"], env=env,
                            capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        return ["Owned worker sessions remain after shutdown"] if result.stdout.strip() else []
    if result.returncode == 1 and ("no server running" in result.stderr or
                                  "No such file or directory" in result.stderr):
        return []
    return ["Could not verify owned worker-session cleanup: " + result.stderr.strip()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", type=pathlib.Path)
    p.add_argument("--minutes", type=float, default=20)
    a = p.parse_args()
    run = a.run.resolve()
    manifest = json.loads((run / "run.json").read_text())
    city = run / "city"
    if pathlib.Path(manifest["city"]).resolve() != city:
        p.error("Run manifest does not identify this city")
    env = isolated_env(run)
    env["PATH"] = ":".join(manifest["tool_bin_dirs"]) + ":" + env["PATH"]
    env["BEADS_DIR"] = str(city / ".beads")
    env["BEADS_DOLT_AUTO_START"] = "0"
    require_claude_auth(env)
    projects = json.loads((pathlib.Path.home() / ".claude.json").read_text()).get("projects", {})
    if not any(pathlib.Path(path).resolve() == city and value.get("hasTrustDialogAccepted") for path, value in projects.items()):
        p.error(f"Before launching, open Claude in {city}, trust this demo folder, then exit. No agents were started.")
    evidence = city / "evidence"
    evidence.mkdir(exist_ok=False)
    baseline = fixed_hashes(city)
    (evidence / "fixed-files.json").write_text(json.dumps(baseline, indent=2) + "\n")
    def command(args, timeout=60):
        result = subprocess.run(args, cwd=city, env=env, capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError(f"{args}: {result.stderr or result.stdout}")
        return result.stdout
    versions = {name: command([name, flag]).strip() for name, flag in (("gc", "version"), ("bd", "version"), ("claude", "--version"), ("tmux", "-V"), ("dolt", "version"))}
    status = {"outcome": "incomplete", "started_at": datetime.now(timezone.utc).isoformat(), "versions": versions}
    print("[1/4] Start the owned supervisor on its isolated API port", flush=True)
    # Seed this NEW private registry before starting its foreground supervisor.
    # gc start/register always installs a platform service in the pinned release.
    registry = run / "home/cities.toml"
    with registry.open("x") as stream:
        stream.write(f'[[cities]]\npath = {json.dumps(str(city))}\nname = {json.dumps(manifest["name"])}\n')
    log = (run / "supervisor-process.log").open("w")
    supervisor = subprocess.Popen(["gc", "supervisor", "run"], cwd=city, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(60):
            if supervisor.poll() is not None:
                raise RuntimeError(f"Supervisor exited {supervisor.returncode}; see {run / 'supervisor-process.log'}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{manifest['port']}/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(1)
        else:
            raise TimeoutError("Supervisor API did not become ready within 60 seconds")
        for _ in range(300):
            if supervisor.poll() is not None:
                raise RuntimeError("Supervisor exited during city startup")
            with urllib.request.urlopen(f"http://127.0.0.1:{manifest['port']}/v0/cities", timeout=5) as response:
                cities = json.load(response)
            if any(c.get("running") for c in cities.get("items", []) if c.get("name") == manifest["name"]):
                break
            time.sleep(1)
        else:
            raise TimeoutError("City did not become ready within 300 seconds")
        print("[2/4] Instantiate two coding tasks and their integration dependency", flush=True)
        dispatch = json.loads(command(["gc", "sling", "coder", "parallel-summary", "--formula", "--json"], timeout=120))
        (evidence / "dispatch.json").write_text(json.dumps(dispatch, indent=2) + "\n")
        workflow = dispatch["workflow_id"]
        status["workflow_id"] = workflow
        print("[3/4] Observe three tasks, ready work, sessions and runtime; no mutating rescue", flush=True)
        rows = observe(command, env, manifest, evidence, workflow, a.minutes, supervisor)
        print("[4/4] Verify fixed files, task overlap, dependency order and final artifact", flush=True)
        if baseline != fixed_hashes(city):
            raise RuntimeError("Workers changed fixed tests, scripts or configuration")
        command([sys.executable, "scripts/check_parts.py", "all"])
        proof = verify(city, rows)
        (evidence / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
        status.update(outcome="pass", fixed_files_unchanged=True)
    except BaseException as error:
        status.update(outcome="fail", error=str(error) or type(error).__name__)
        raise
    finally:
        status["verification_finished_at"] = datetime.now(timezone.utc).isoformat()
        cleanup_started = time.monotonic()
        print("[cleanup] Stop supervisor, workers and owned database", flush=True)
        # Foreground supervisor owns and stops its cities on SIGTERM. No
        # platform service or preserve-sessions flag is present in our env.
        errors = stop_supervisor(supervisor)
        try:
            errors.extend(session_cleanup_errors(env, manifest["name"]))
        except subprocess.TimeoutExpired:
            errors.append("Owned worker-session cleanup check timed out")
        if not errors:
            try:
                status["database_cleanup"] = cleanup_database(city, env)
            except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
                errors.append("Database cleanup: " + str(error))
        log.close()
        status["supervisor_exit_code"] = supervisor.returncode
        status["cleanup_seconds"] = round(time.monotonic() - cleanup_started, 3)
        status["finished_at"] = datetime.now(timezone.utc).isoformat()
        status["cleanup_errors"] = errors
        if errors:
            status["outcome"] = "fail"
        (evidence / "run.json").write_text(json.dumps(status, indent=2) + "\n")
        print(json.dumps(status, indent=2), flush=True)
        if errors:
            raise RuntimeError("Run cleanup failed; see evidence/run.json")


if __name__ == "__main__":
    main()
