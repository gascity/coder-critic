#!/bin/sh
# Prepare an isolated runtime. Does not start agents or overwrite an existing run.
set -eu
if [ "$#" -ne 1 ]; then
  echo "Usage: sh prepare.sh /absolute/path/to/new-run-directory" >&2
  exit 2
fi
case "$1" in /*) ;; *) echo "Use an absolute run-directory path" >&2; exit 2 ;; esac
DEMO_SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEMO_RUN=$1
if [ -e "$DEMO_RUN" ]; then
  echo "Run directory already exists: $DEMO_RUN" >&2
  exit 2
fi
for tool in gc bd dolt tmux claude python3; do command -v "$tool" >/dev/null; done
DEMO_NAME=$(python3 -c 'import hashlib,sys; print("coder-critic-" + hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])' "$DEMO_RUN")
mkdir -p "$DEMO_RUN/city/agents"
export GC_HOME="$DEMO_RUN/home"
for file in BRIEF.md city.toml pack.toml packs.lock; do
  cp "$DEMO_SOURCE/$file" "$DEMO_RUN/city/$file"
done
for directory in formulas tests scripts; do
  cp -R "$DEMO_SOURCE/$directory" "$DEMO_RUN/city/$directory"
done
for role in coder critic tester reviser verifier; do
  cp -R "$DEMO_SOURCE/agents/$role" "$DEMO_RUN/city/agents/$role"
done
chmod +x "$DEMO_RUN/city/scripts/verify.sh"
echo "[1/2] Initializing isolated city and pinned pack imports"
gc init "$DEMO_RUN/city" --name "$DEMO_NAME" --file "$DEMO_RUN/city/city.toml" --preserve-existing --no-start
echo "[2/2] Compiling the demonstration formula"
gc --city "$DEMO_RUN/city" formula show coder-critic
echo "Prepared $DEMO_RUN. Follow README.md to trust the folder and start the run."
