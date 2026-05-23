#!/usr/bin/env bash
# ── Crusher-to-the-Bridge Dashboard Launcher ──────────────────────────
# Run this from any terminal to launch the Streamlit dashboard.
# It will generate fresh simulation data and open the dashboard.
# ──────────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

echo "[1/2] Running orchestrator (24-epoch simulation)..."
PYTHONIOENCODING=utf-8 python orchestrator.py

echo ""
echo "[2/2] Launching Streamlit dashboard..."
echo "Dashboard will open at http://localhost:8501"
echo "Press Ctrl+C to stop."
echo ""
streamlit run dashboard.py
