@echo off
REM ── Crusher-to-the-Bridge Dashboard Launcher ──────────────────────────
REM Run this from any terminal to launch the Streamlit dashboard.
REM It will generate fresh simulation data and open the dashboard.
REM ──────────────────────────────────────────────────────────────────────

cd /d "%~dp0"

echo [1/2] Running orchestrator (24-epoch simulation)...
set PYTHONIOENCODING=utf-8
python orchestrator.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: orchestrator.py failed. Make sure dependencies are installed:
    echo   pip install pyyaml numpy streamlit plotly pandas
    pause
    exit /b 1
)

echo.
echo [2/2] Launching Streamlit dashboard...
echo Dashboard will open at http://localhost:8501
echo Press Ctrl+C to stop.
echo.
streamlit run dashboard.py
pause
