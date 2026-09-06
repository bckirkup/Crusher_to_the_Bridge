@echo off
REM ── Crusher-to-the-Bridge Dashboard Launcher ──────────────────────────
REM Run this from any terminal to launch the Streamlit dashboard.
REM It will generate fresh simulation data and open the dashboard.
REM ──────────────────────────────────────────────────────────────────────

cd /d "%~dp0"

echo [1/3] Preparing deck blueprint assets (class plates for tactical map)...
set PYTHONIOENCODING=utf-8
python scripts/precompute_deck_assets.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: precompute failed. Install dashboard dependencies:
    echo   uv sync --locked --all-extras --no-install-project --no-build
    pause
    exit /b 1
)

echo.
echo [2/3] Running orchestrator (24-epoch simulation)...
python orchestrator.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: orchestrator.py failed. Make sure dependencies are installed:
    echo   uv sync --locked --all-extras --no-install-project --no-build
    pause
    exit /b 1
)

echo.
echo [3/3] Launching Streamlit dashboard...
echo Dashboard will open at http://localhost:8501
echo Press Ctrl+C to stop.
echo.
streamlit run dashboard.py
pause
