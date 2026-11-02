#!/bin/sh
# Offline application smoke test; building downloads build tools if not cached.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
python3 -m venv "$work/build"
"$work/build/bin/python" -m pip install build
"$work/build/bin/python" -m build "$root" --outdir "$work/dist"
python3 -m venv "$work/run"
"$work/run/bin/python" -m pip install --no-deps "$work"/dist/*.whl
cd "$work"
"$work/run/bin/cb" --help
"$work/run/bin/python" -m codbeing model status
"$work/run/bin/cb" example nomusa --trace-file "$work/traces/example.json" --reports-dir "$work/reports"
"$work/run/bin/cb" run "$work/traces/example.json" --reports-dir "$work/reports" --name installed-replay
