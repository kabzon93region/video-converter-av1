# Конвертер видео в формат AV1

Этот проект представляет собой графический конвертер видео, написанный на Python с использованием библиотеки Tkinter для создания пользовательского интерфейса и ffmpeg для конвертации видео в формат AV1 с помощью кодека libsvtav1.

## Описание

Программа позволяет пользователю выбирать папку с видеофайлами, настраивать параметры конвертации (CRF, preset, фильтр по высоте) и выполнять конвертацию всех подходящих видеофайлов в формат AV1. Основные возможности:

- Конвертация видео с использованием ffmpeg и кодека libsvtav1.
- Получение информации о видео с помощью ffprobe (высота, количество кадров).
- Удобный графический интерфейс с темной темой, имитирующей VS Code.
- Логирование действий и ошибок с помощью loguru.
- Опциональное удаление исходных файлов после успешной конвертации.

## Требования

- Python 3.6 и выше
- ffmpeg (должен быть установлен и доступен в PATH)
- Python-библиотеки: tkinter (стандартная), loguru

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/kabzon93region/video-converter-av1.git
   ```
2. Перейдите в директорию проекта:
   ```bash
   cd video-converter-av1
   ```
3. Установите зависимости:
   ```bash
   pip install loguru
   ```
4. Убедитесь, что ffmpeg установлен и доступен в PATH.

## Использование

1. Запустите программу:
   ```bash
   python vo.py
   ```
2. Укажите параметры конвертации в графическом интерфейсе:
   - Папка с видео
   - Параметры: preset, CRF, фильтр по высоте
   - Опционально: удаление исходных файлов
3. Нажмите кнопку "Запустить конвертацию".

## Сборка

Для сборки исполняемого файла используется PyInstaller. Запустите скрипт `build.cmd` для сборки:

```bash
pyinstaller --onefile --windowed --noconsole vo.py
```

## Вклад и Разработка

Если вы хотите внести свой вклад, создайте форк репозитория, внесите изменения и отправьте pull request. Для сообщений об ошибках используйте раздел [Issues](https://github.com/kabzon93region/video-converter-av1/issues).

## Лицензия

Этот проект распространяется под лицензией MIT. Подробности см. в файле [LICENSE](https://opensource.org/licenses/MIT).

## Контакты

Если у вас есть вопросы или предложения, вы можете связаться со мной по электронной почте: [kabzon93region@gmail.com](mailto:kabzon93region@gmail.com). 