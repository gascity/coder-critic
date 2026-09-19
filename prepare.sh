#!/bin/sh
# Prepare an isolated runtime. Does not start agents or overwrite an existing run.
set -eu
DEMO_SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$DEMO_SOURCE/scripts/prepare_runtime.py" "$@"
