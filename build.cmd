@echo off
chcp 65001
@cls
echo Скрипт для сборки exe-файла из Python-программы с использованием PyInstaller
echo Устанавливаем PyInstaller (если еще не установлен)
pip install pyinstaller
 
@cls
echo Скрипт для сборки exe-файла из Python-программы с использованием PyInstaller
echo OK - Устанавливаем PyInstaller (если еще не установлен)
echo Очистка предыдущих сборок
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist vo.spec del vo.spec

@cls
echo Скрипт для сборки exe-файла из Python-программы с использованием PyInstaller
echo OK - Устанавливаем PyInstaller (если еще не установлен)
echo OK - Очистка предыдущих сборок
echo Сборка exe-файла (флаг --windowed для GUI-приложения, --onefile объединяет все в один файл)
pyinstaller --onefile --windowed --noconsole vo.py

echo !_Готово_! =<^_^>=
pause
