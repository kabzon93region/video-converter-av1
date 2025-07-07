@chcp 65001
@echo off
setlocal enabledelayedexpansion
set "PYTHONUTF8=1"

REM --- Script directory ---
pushd "%~dp0"
 
REM --- Virtual environment ---
set "VENV_DIR=%~dp0vo_venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    python -m venv "%VENV_DIR%"
)
call "%VENV_DIR%\Scripts\activate"

echo Done. Starting program.
python vo.py

echo Program finished.
pause