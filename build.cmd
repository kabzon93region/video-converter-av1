@echo off
chcp 65001
REM Скрипт для сборки exe-файла из Python-программы с использованием PyInstaller

REM Устанавливаем PyInstaller (если еще не установлен)
pip install pyinstaller

REM Очистка предыдущих сборок
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist vo.spec del vo.spec

REM Сборка exe-файла (флаг --windowed для GUI-приложения, --onefile объединяет все в один файл)
pyinstaller --onefile --windowed --noconsole vo.py

pause
