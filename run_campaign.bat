@echo off
setlocal EnableExtensions
REM ============================================================================
REM  run_campaign.bat — Mega Cruise ~17780 Picard campaign (Windows)
REM
REM  Prerequisites:
REM    - Python 3.11+ on PATH as "python" or "python3"
REM    - pip install -r requirements.txt  (from repo root)
REM
REM  From the repo root (or double-click this file):
REM    run_campaign.bat --smoke
REM    run_campaign.bat --tier t1
REM    run_campaign.bat --dry-run
REM    run_campaign.bat --resume --tier t2
REM ============================================================================

cd /d "%~dp0"

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where python3 >nul 2>&1 && set "PY=python3"
)
if not defined PY (
  echo ERROR: Neither python nor python3 found on PATH.
  echo Install Python 3.11+ and ensure it is on PATH.
  exit /b 1
)

set PYTHONUTF8=1
set PYTHONPATH=%CD%

echo.
echo === Crusher mega cruise campaign ===
echo Repo: %CD%
echo Python: %PY%
echo.

"%PY%" picard_framework\runs\mega_cruise_campaign\campaign_runner.py %*
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo Campaign exited with code %EC%.
  exit /b %EC%
)
exit /b 0
