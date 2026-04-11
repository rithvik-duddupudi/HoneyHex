#!/usr/bin/env bash
# Run a minimal HoneyHex demo in a temporary directory (no Redis/registry required).
set -euo pipefail

if ! command -v hex >/dev/null 2>&1; then
  echo "hex not found on PATH."
  echo "From the HoneyHex repo: python3.12 -m venv .venv && source .venv/bin/activate && pip install -e ."
  exit 1
fi

WORKSPACE="$(mktemp -d "${TMPDIR:-/tmp}/honeyhex-demo.XXXXXX")"
cleanup() {
  rm -rf "$WORKSPACE"
}
trap cleanup EXIT

cd "$WORKSPACE"
echo "=== HoneyHex demo workspace: $WORKSPACE ==="
echo

echo ">>> hex cell init"
hex cell init
echo

echo ">>> hex commit (two thought-commits)"
hex commit -m "Understand the task" \
  --prompt "User wants a short local demo of HoneyHex." \
  --scratchpad "Plan: init cell, commit twice, show log."
hex commit -m "Execute the demo" \
  --prompt "Same task" \
  --scratchpad "Running scripted commits and inspection commands."
echo

echo ">>> hex log --oneline"
hex log --oneline
echo

echo ">>> hex show HEAD (excerpt)"
hex show HEAD | head -n 40
echo

echo "=== Done. This folder was temporary and has been removed. ==="
echo "To keep a cell, create a directory, run hex cell init, and hex commit from there."
