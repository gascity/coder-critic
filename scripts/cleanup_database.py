"""Stop only this city's database and catch late restarts after worker teardown."""
import argparse
import json
import pathlib
import socket
import subprocess
import time
from runtime_common import isolated_env


def port_open(port):
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def owned_ports(city):
    city = city.resolve()
    expected_data = (city / ".beads/dolt").resolve()
    ports = set()
    # GC removes live state during a clean stop but retains provider state.
    for name in ("dolt-state.json", "dolt-provider-state.json"):
        path = city / ".gc/runtime/packs/dolt" / name
        if path.exists():
            state = json.loads(path.read_text())
            if pathlib.Path(state["data_dir"]).resolve() != expected_data:
                raise RuntimeError("Database state does not belong to this city's data directory")
            port = state["port"]
            if type(port) is not int or not 0 < port < 65536:
                raise RuntimeError("Invalid owned database port")
            ports.add(port)
    return ports


def cleanup_database(city, env, timeout=120, quiet_seconds=15):
    city = city.resolve()
    deadline = time.monotonic() + timeout
    quiet_since = None
    ports = set()
    attempts = 0
    while time.monotonic() < deadline:
        ports.update(owned_ports(city))
        listening = [port for port in sorted(ports) if port_open(port)]
        if listening:
            quiet_since = None
            for port in listening:
                # GC validates process ownership and waits for store locks.
                # Never kill a PID ourselves or delete any database files.
                result = subprocess.run(
                    ["gc", "dolt-state", "stop-managed", "--city", str(city), "--port", str(port)],
                    cwd=city, env=env, capture_output=True, text=True,
                    timeout=max(1, deadline - time.monotonic()))
                attempts += 1
                if result.returncode:
                    raise RuntimeError("Owned database stop failed; data files were retained")
        else:
            if quiet_since is None:
                quiet_since = time.monotonic()
            if time.monotonic() - quiet_since >= quiet_seconds:
                if not ports:
                    raise RuntimeError("No owned database endpoint available for verification")
                return {"verified": True, "ports": sorted(ports),
                        "stop_attempts": attempts, "quiet_seconds": quiet_seconds}
        time.sleep(1)
    raise TimeoutError("Owned database did not stay stopped within cleanup deadline")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=pathlib.Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest = json.loads((run / "run.json").read_text())
    city = run / "city"
    if pathlib.Path(manifest["city"]).resolve() != city:
        parser.error("Run manifest does not identify this city")
    env = isolated_env(run)
    env["PATH"] = ":".join(manifest["tool_bin_dirs"]) + ":" + env["PATH"]
    env["BEADS_DOLT_AUTO_START"] = "0"
    print(json.dumps(cleanup_database(city, env), indent=2))
