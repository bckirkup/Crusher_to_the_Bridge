#!/usr/bin/env bash
# ============================================================================
#  run_campaign.sh — Mega Cruise ~17780 Picard campaign (Linux / macOS)
#
#  From the repo root:
#    ./run_campaign.sh --smoke
#    ./run_campaign.sh --tier t1
#    ./run_campaign.sh --dry-run
#    ./run_campaign.sh --resume --tier t2
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONUTF8=1
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "ERROR: Neither python3 nor python found on PATH." >&2
  exit 1
fi

echo ""
echo "=== Crusher mega cruise campaign ==="
echo "Repo: $ROOT"
echo "Python: $PY"
echo ""

exec "$PY" picard_framework/runs/mega_cruise_campaign/campaign_runner.py "$@"
