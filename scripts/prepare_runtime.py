"""Create a new owned runtime; never attach to or migrate an existing database."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

from runtime_common import available_port, isolated_env, require_claude_auth

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", type=pathlib.Path)
    a = p.parse_args()
    if not a.run.is_absolute():
        p.error("Use an absolute new run directory")
    run = a.run.resolve()
    if run.exists():
        p.error(f"Refusing to overwrite existing run directory: {run}")
    env = isolated_env(run)
    for tool in ("gc", "bd", "dolt", "tmux", "claude", "python3"):
        if not shutil.which(tool):
            p.error(f"Missing required tool: {tool}")
    require_claude_auth(env)
    # Even `gc version` may create GC_HOME: reserve the owned root first.
    run.mkdir(parents=True, exist_ok=False)
    for command, expected in ((["gc", "version"], "1.4.1"), (["bd", "version"], "bd version 1.2.2 (Homebrew)"), (["dolt", "version"], "dolt version 2.3.1")):
        actual = subprocess.check_output(command, env=env, text=True, timeout=15).strip()
        if command[0] == "bd":
            valid = actual.startswith("bd version 1.2.2 ")
        else:
            valid = actual.splitlines()[0] == expected
        if not valid:
            p.error(f"Expected {expected}; found {actual}")
    city, home = run / "city", run / "home"
    city.mkdir()
    home.mkdir(exist_ok=True)
    name = "parallel-" + hashlib.sha256(str(run).encode()).hexdigest()[:12]
    port = available_port()
    (home / "supervisor.toml").write_text(f'[supervisor]\nport = {port}\nbind = "127.0.0.1"\n')
    for file in ("BRIEF.md", "city.toml", "pack.toml", "packs.lock"):
        shutil.copy2(ROOT / file, city / file)
    for directory in ("agents", "formulas", "tests", "tests_parts", "scripts"):
        shutil.copytree(ROOT / directory, city / directory, ignore=shutil.ignore_patterns("__pycache__"))
    (city / "reports").mkdir()
    (city / "scripts/verify_parallel.sh").chmod(0o755)
    def command(argv):
        subprocess.run(argv, cwd=city, env=env, check=True, timeout=600)
    print("[1/2] Initialize isolated Gas City and fetch pinned packs", flush=True)
    # Seed the brand-new schema before GC writes its metadata stub. Otherwise
    # bd init --force's five-second issue-count preflight may partially migrate it.
    command(["bd", "init", "--database", "hq", "--prefix", "demo", "--skip-hooks", "--skip-agents", "--non-interactive"])
    # bd's embedded and GC's managed-server modes use distinct data roots.
    # Copy only this newly initialized, closed database into the new server root.
    shutil.copytree(city / ".beads/embeddeddolt/hq", city / ".beads/dolt/hq")
    # Authentication was explicitly verified above with a 30-second budget;
    # do not repeat GC 1.4.1's five-second probe during offline preparation.
    command(["gc", "init", str(city), "--name", name, "--file", str(city / "city.toml"), "--preserve-existing", "--no-start", "--skip-provider-readiness"])
    print("[2/2] Compile the parallel task graph", flush=True)
    command(["gc", "formula", "show", "parallel-summary"])
    tool_dirs = list(dict.fromkeys(str(pathlib.Path(shutil.which(tool)).resolve().parent) for tool in ("gc", "bd", "dolt")))
    (run / "run.json").write_text(json.dumps({"city": str(city), "name": name, "port": port, "tool_bin_dirs": tool_dirs}, indent=2) + "\n")
    print(f"Prepared {run}. Trust this city folder once with Claude before running; see README.md.", flush=True)


if __name__ == "__main__":
    main()
