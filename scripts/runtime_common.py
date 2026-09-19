"""Isolation shared by preparation and the live runner."""
import os
import json
import pathlib
import socket
import subprocess


def require_claude_auth(env):
    try:
        result = subprocess.run(["claude", "auth", "status", "--json"], env=env,
                                capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Claude authentication check exceeded 30 seconds; no workers started") from error
    try:
        if result.returncode:
            raise ValueError("probe failed")
        status = json.loads(result.stdout)
        if not isinstance(status, dict):
            raise ValueError("invalid status")
    except ValueError as error:
        raise RuntimeError("Could not verify Claude authentication; run claude auth status --json") from error
    if status.get("loggedIn") is not True:
        raise RuntimeError("Authenticate Claude before running this sample; no workers started")


def isolated_env(run):
    # Never inherit another city's endpoint, session, database or service unit.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("GC_", "BD_", "BEADS_")) and k not in ("TMUX", "TMUX_PANE", "CLAUDECODE")}
    env["GC_HOME"] = str(pathlib.Path(run).resolve() / "home")
    env["DISABLE_AUTOUPDATER"] = "1"
    return env


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
