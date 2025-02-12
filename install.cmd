@echo off
@chcp 65001
echo Проверка наличия ffmpeg
where ffmpeg >nul 2>&1
if %ERRORLEVEL%==0 (
    echo ffmpeg обнаружен.
    goto end
)
echo ffmpeg не найден. 
echo Скачайте ffmpeg для windows. Перенесите архив ffmpeg в текущую папку. Переименуйте архив ffmpeg в ffmpeg.zip и нажмите любую клавишу для снятия паузы и продолжения установки ffmpeg из вашего архива.
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
pause
