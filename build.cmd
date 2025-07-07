@chcp 65001
@echo off
@cls
echo Script to build an executable from a Python program using PyInstaller
echo Installing PyInstaller (if not already installed)
pip install pyinstaller
 
@cls
echo Script to build an executable from a Python program using PyInstaller
echo OK - Installing PyInstaller (if not already installed)
echo Cleaning up previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist vo.spec del vo.spec

@cls
echo Script to build an executable from a Python program using PyInstaller
echo OK - Installing PyInstaller (if not already installed)
echo OK - Cleaning up previous builds
echo Building executable ( --windowed for GUI app, --onefile combines everything into one file)
pyinstaller --onefile --windowed --noconsole vo.py

echo !_Done_! =<^_^>=
pause
