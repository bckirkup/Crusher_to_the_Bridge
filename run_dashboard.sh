#!/usr/bin/env bash
# ── Crusher-to-the-Bridge Dashboard Launcher ──────────────────────────
# Run this from any terminal to launch the Streamlit dashboard.
# It will generate fresh simulation data and open the dashboard.
# ──────────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

echo "[1/3] Preparing deck blueprint assets (class plates for tactical map)..."
PYTHONIOENCODING=utf-8 python3 scripts/precompute_deck_assets.py

echo ""
echo "[2/3] Running orchestrator (24-epoch simulation)..."
PYTHONIOENCODING=utf-8 python3 orchestrator.py

echo ""
echo "[3/3] Launching Streamlit dashboard..."
echo "Dashboard will open at http://localhost:8501"
echo "Press Ctrl+C to stop."
echo ""
streamlit run dashboard.py
