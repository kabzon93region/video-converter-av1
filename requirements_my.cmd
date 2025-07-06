@echo off
chcp 65001
setlocal enabledelayedexpansion
set "PYTHONUTF8=1"

REM --- каталог скрипта ---
pushd "%~dp0"

REM --- виртуальное окружение ---
set "VENV_DIR=%~dp0vo_venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    python -m venv "%VENV_DIR%"
)
call "%VENV_DIR%\Scripts\activate"

REM --- requirements ---
python -m pip freeze | findstr /v "pip setuptools wheel easy_install" > requirements_my.txt
echo Список пакетов (без системных) сохранен в requirements_my.txt
pause