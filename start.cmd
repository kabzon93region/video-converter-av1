@chcp 65001
@echo off
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

echo Готово. Запускаем программу.
python vo.py

echo Программа завершилась.
pause