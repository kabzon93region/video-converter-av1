@echo off
@chcp 65001
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

echo Проверка наличия ffmpeg
where ffmpeg >nul 2>&1
if %ERRORLEVEL%==0 (
    echo ffmpeg обнаружен.
    goto end
)
echo ffmpeg не найден. 
echo Скачайте ffmpeg для windows. Перенесите архив ffmpeg в текущую папку. Переименуйте архив ffmpeg в ffmpeg.zip и нажмите любую клавишу для снятия паузы и продолжения установки ffmpeg из вашего архива. 
echo (если скачали с гитхаба архив для винды, то в нем есть подходящий архив с ffmpeg.zip).

pause

echo Создаем директорию C:\ffmpeg, если её нет.
if not exist "C:\ffmpeg" mkdir "C:\ffmpeg"
echo Распаковываем архив ffmpeg.zip в C:\ffmpeg с помощью PowerShell.
powershell -Command "Expand-Archive -Force -Path 'ffmpeg.zip' -DestinationPath 'C:\ffmpeg'"
echo Добавляем C:\ffmpeg\bin в PATH для текущей сессии и навсегда.
set PATH=C:\ffmpeg\bin;%PATH%
setx PATH "C:\ffmpeg\bin;%PATH%"
echo ffmpeg успешно установлен и PATH обновлен.
:end


echo Установка requirements
python -m pip install --upgrade pip setuptools wheel
python -m pip check
python -m pip cache purge
python -m pip check
pip install -r requirements.txt
python -m pip check
python -m pip cache purge
python -m pip check

echo Готово. Запускаем программу.
python vo.py

echo Программа завершилась.
pause