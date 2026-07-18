@echo off
setlocal EnableExtensions
REM ============================================================================
REM  run_contam_compare.bat — native vs ContamX results + speed suite (Windows)
REM
REM  Prerequisites:
REM    - Python 3.11+ on PATH as "python"
REM    - ContamX binary under third_party\contamx\  (e.g. ContamX3.exe)
REM      OR set CONTAMX_BINARY / CONTAMX_HOME
REM
REM  From the repo root (or double-click this file):
REM    run_contam_compare.bat
REM    run_contam_compare.bat --job data\config\contam_compare\jobs\destroyer_transport.json
REM ============================================================================

cd /d "%~dp0"

if not defined CONTAMX_BINARY (
  if exist "%~dp0third_party\contamx\ContamX3.exe" (
    set "CONTAMX_BINARY=%~dp0third_party\contamx\ContamX3.exe"
  ) else if exist "%~dp0third_party\contamx\contamx3.exe" (
    set "CONTAMX_BINARY=%~dp0third_party\contamx\contamx3.exe"
  ) else if exist "%~dp0third_party\contamx\ContamX.exe" (
    set "CONTAMX_BINARY=%~dp0third_party\contamx\ContamX.exe"
  )
)

if not defined CONTAMX_HOME (
  if exist "%~dp0third_party\contamx\" (
    set "CONTAMX_HOME=%~dp0third_party\contamx"
  )
)

echo.
echo === Crusher Contam engine compare ===
echo Repo: %CD%
if defined CONTAMX_BINARY (
  echo CONTAMX_BINARY=%CONTAMX_BINARY%
) else if defined CONTAMX_HOME (
  echo CONTAMX_HOME=%CONTAMX_HOME%
) else (
  echo ContamX not found under third_party\contamx — native-only runs.
  echo See third_party\contamx\README.md
)
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: python not found on PATH. Install Python 3.11+ and retry.
  exit /b 1
)

if "%~1"=="" (
  python tools\contam_engine_compare.py --suite data\config\contam_compare\suite.json
) else (
  python tools\contam_engine_compare.py %*
)

set "EXITCODE=%ERRORLEVEL%"
echo.
echo Reports land in telemetry_buffer\contam_compare\  ^(gitignored^)
exit /b %EXITCODE%
