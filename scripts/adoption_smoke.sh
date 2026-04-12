#!/usr/bin/env bash
# Adoption smoke: run from a repo with `hex` on PATH (e.g. pip install -e ".[dev]").
set -euo pipefail
HEX="${HEX:-hex}"
if ! command -v "$HEX" >/dev/null 2>&1; then
  echo "hex not found; set HEX or install honeyhex (pip install -e .)" >&2
  exit 1
fi
TMP="${TMPDIR:-/tmp}/honeyhex-smoke-$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
"$HEX" cell init --guided
"$HEX" doctor
"$HEX" validate
"$HEX" export --format md -n 3
"$HEX" audit HEAD
echo "adoption_smoke: ok"
