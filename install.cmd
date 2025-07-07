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

echo Checking for ffmpeg
where ffmpeg >nul 2>&1
if %ERRORLEVEL%==0 (
    echo ffmpeg detected.
    goto end
)
echo ffmpeg not found.
echo Download ffmpeg for windows. Move the ffmpeg archive to the current folder. Rename the ffmpeg archive to ffmpeg.zip and press any key to unpause and continue installing ffmpeg from your archive.
echo (If you downloaded the Windows archive from GitHub, it contains a suitable ffmpeg.zip archive).

pause

echo Creating C:\ffmpeg directory if it doesn't exist.
if not exist "C:\ffmpeg" mkdir "C:\ffmpeg"
echo Unpacking ffmpeg.zip to C:\ffmpeg using PowerShell.
powershell -Command "Expand-Archive -Force -Path 'ffmpeg.zip' -DestinationPath 'C:\ffmpeg'"
echo Adding C:\ffmpeg\bin to PATH for current session and permanently.
set PATH=C:\ffmpeg\bin;%PATH%
setx PATH "C:\ffmpeg\bin;%PATH%"
echo ffmpeg successfully installed and PATH updated.
:end


echo Installing requirements
python -m pip install --upgrade pip setuptools wheel
python -m pip check
python -m pip cache purge
python -m pip check
pip install -r requirements.txt
python -m pip check
python -m pip cache purge
python -m pip check

echo Done. Starting program.
python vo.py

echo Program finished.
pause