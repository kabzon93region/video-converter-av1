import os                # Импортируется модуль os для работы с операционной системой и выполнения операций с файлами
import sys               # Импортируется модуль sys для доступа к системным функциям и переменным интерпретатора
import subprocess        # Импортируется модуль subprocess для выполнения внешних команд и запуска процессов
import threading         # Импортируется модуль threading для работы с потоками и параллельного выполнения кода
import time              # Импортируется модуль time для работы со временем, измерения задержек и отсчетов
import tkinter as tk     # Импортируется библиотека tkinter для создания графического интерфейса
from tkinter import filedialog, messagebox  # Импортируются диалоговые окна для выбора файлов и вывода сообщений пользователю
from tkinter import ttk  # Импортируется ttk для использования расширенных виджетов (например, Progressbar) с улучшенной стилизацией
from loguru import logger  # Импортируется библиотека loguru для ведения логирования и отладки
import datetime  # Импортируется модуль datetime для работы с датой и временем, используется при формировании имени лога
from functools import partial  # Импортируется функция partial для создания частично применяемых функций, упрощающих вызовы
import re                 # Импортируется модуль re для работы с регулярными выражениями и поиска шаблонов

log_dir = "logs"  # Задается имя директории для хранения логов
os.makedirs(log_dir, exist_ok=True)  # Создается директория для логов, если она еще не существует
log_filename = os.path.join(log_dir, "vo_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log")  # Формируется имя файла лога с текущей датой и временем
logger.add(log_filename, rotation="1 MB", compression="zip")  # Добавляется файл логирования с ротацией при достижении 1 МБ и сжатием в zip
# Глобальные переменные для управления процессом конвертации, таймером и флагом завершения
stop_requested = False  # Флаг, сигнализирующий о запросе остановки конвертации
current_conversion_process = None  # Переменная для хранения текущего процесса конвертации (ffmpeg)
current_output_file = None  # Переменная для хранения имени выходного файла текущей конвертации
conversion_start_time = None  # Переменная для хранения времени начала конвертации
conversion_finished = False  # Флаг, показывающий, что процесс конвертации завершен
timer_id = None  # Идентификатор запланированного обновления таймера


def get_video_height(file_path):  # Функция для получения высоты видео в пикселях с помощью ffprobe
    """
    Получение высоты видео (в пикселях) с помощью ffprobe.
    Если не удается получить высоту, возвращает None.
    """
    try:  # Попытка выполнить получение высоты видео
        cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "{file_path}"'  # Формируется команда ffprobe для извлечения высоты видео
        logger.debug(f"Команда для получения высоты: {cmd}")  # Логирование сформированной команды для отладки
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)  # Запуск внешнего процесса ffprobe и получение вывода
        height_str = result.stdout.strip()  # Извлекается и очищается строка с высотой видео
        if not height_str:  # Если строка пустая (высота не определена)
            logger.warning(f"Высота не обнаружена для файла {file_path}")  # Логирование предупреждения о неудаче получения высоты
            return None  # Возвращается None, если высота не получена
        height = int(height_str)  # Преобразование строки в целое число – высоту видео
        logger.debug(f"Высота файла {file_path}: {height} пикселей")  # Логирование полученной высоты для отладки
        return height  # Возвращение высоты видео
    except Exception as ex:  # Обработка исключений при выполнении команды
        logger.error(f"Ошибка при получении высоты видео для файла {file_path}: {ex}")  # Логирование ошибки с описанием исключения
        return None  # Возвращается None в случае ошибки


def update_estimated_time_label(time_sec):  # Функция обновления метки с оценочным временем конвертации
    estimated_time_label.config(text=f"Оценочное время: {time_sec} сек")  # Обновление текста метки с выводом оценочного времени в секундах


def get_total_frames(file_path):  # Функция для получения общего количества кадров в видеофайле через ffprobe
    """
    Получает общее количество кадров в видеофайле с помощью ffprobe.
    """
    try:  # Попытка выполнить команду для получения количества кадров
        cmd = f'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=nokey=1:noprint_wrappers=1 "{file_path}"'  # Формируется команда ffprobe для подсчета кадров
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)  # Запуск команды и получение вывода
        frames_str = result.stdout.strip()  # Извлечение строки с количеством кадров и ее очистка от лишних пробелов
        if frames_str:  # Если строка с данными присутствует
            total = int(frames_str)  # Преобразование строки в целое число (общее количество кадров)
            logger.debug(f"Общее количество кадров для файла {file_path}: {total}")  # Логирование полученного количества кадров
            return total  # Возвращение общего количества кадров
        else:
            logger.warning(f"Не удалось получить количество кадров для {file_path}")  # Логирование предупреждения, если данные не получены
            return None  # Возвращение None при отсутствии данных
    except Exception as ex:  # Обработка исключений
        logger.error(f"Ошибка при получении количества кадров для файла {file_path}: {ex}")  # Логирование возникшей ошибки
        return None  # Возвращение None в случае ошибки


def update_total_frames_label(current, total):  # Функция обновления метки, показывающей текущее и общее количество кадров
    total_frames_label.config(text=f"Количество кадров: {current}/{total}")  # Установка нового текста метки с информацией о количестве обработанных и общих кадрах


def convert_file(file_path, preset, crf, should_delete_source):  # Функция для конвертации одного видеофайла с помощью ffmpeg и кодека libsvtav1
    """
    Конвертация одного файла через ffmpeg с использованием libsvtav1.
    Выходной файл сохраняется в той же директории с добавлением суффикса '_av1'.
    Запуск конвертации происходит сразу, а получение общего количества кадров
    выполняется в отдельном потоке. Пока общее число кадров не получено, прогресс остается 0.
    Обновляются только fps и количество обработанных кадров.
    """
    base, ext = os.path.splitext(file_path)  # Разделение пути на базовое имя и расширение файла
    output_file = base + "_av1" + ext  # Формирование имени выходного файла с добавлением суффикса '_av1'
    total_frames_holder = {"value": None}  # Создание словаря для хранения общего количества кадров, полученного в потоке
    last_frame = 0  # Инициализация переменной для хранения последнего обработанного кадра

    # Добавляем переменную для процесса ffprobe
    ffprobe_process = None  # Инициализация переменной для хранения процесса ffprobe

    # Фоновый поток для получения общего количества кадров, с возможностью завершения процесса ffprobe
    def fetch_total_frames():  # Функция, запускаемая в отдельном потоке для получения числа кадров
        nonlocal ffprobe_process  # Объявление переменной ffprobe_process как недоступной только для локального контекста
        try:
            cmd_ffprobe = f'ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=nokey=1:noprint_wrappers=1 "{file_path}"'  # Формирование команды для получения числа кадров с помощью ffprobe
            ffprobe_process = subprocess.Popen(cmd_ffprobe, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)  # Запуск процесса ffprobe
            out, err = ffprobe_process.communicate()  # Чтение вывода и ошибок из процесса
            total = int(out.strip()) if out.strip() else None  # Преобразование полученного вывода в число, если данные присутствуют
            total_frames_holder["value"] = total  # Сохранение полученного значения общего числа кадров
        except Exception as ex:  # Обработка исключений во время выполнения
            logger.error(f"Ошибка при получении количества кадров для файла {file_path}: {ex}")  # Логирование ошибки
            total_frames_holder["value"] = None  # Запись None в случае ошибки получения данных
        finally:
            root.after(0, update_total_frames_label, last_frame, total_frames_holder["value"] if total_frames_holder["value"] is not None else "N/A")  # Обновление метки с количеством кадров в интерфейсе
    threading.Thread(target=fetch_total_frames, daemon=True).start()  # Запуск фонового потока для выполнения функции fetch_total_frames

    # Изначально обновляем метку: общее число кадров неизвестно
    root.after(0, update_total_frames_label, 0, "N/A")  # Установка начального состояния метки с информацией о кадрах
    
    cmd = [  # Формирование списка аргументов для команды ffmpeg
        "ffmpeg",             # Имя программы для конвертации видео
        "-y",                 # Параметр для автоматического подтверждения перезаписи выходного файла
        "-i", file_path,      # Указание входного файла
        "-c:v", "libsvtav1",  # Выбор видеокодека libsvtav1 для конвертации
        "-crf", str(crf),     # Параметр качества (CRF), преобразованный в строку
        "-preset", str(preset),  # Предустановка скорости конвертации, преобразованная в строку
        "-progress", "pipe:1",   # Параметр для вывода прогресса конвертации через pipe
        output_file          # Имя выходного файла, куда будет сохранено конвертированное видео
    ]
    logger.info(f"Начало конвертации файла: {file_path}")  # Логирование начала процесса конвертации для данного файла
    logger.debug(f"Команда конвертации: {' '.join(cmd)}")  # Логирование сформированной команды для отладки
    try:
        global current_conversion_process, current_output_file  # Объявление глобальных переменных для хранения текущего процесса и выходного файла
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW)  # Запуск процесса ffmpeg для конвертации без создания окна консоли
        current_conversion_process = process  # Сохранение запущенного процесса в глобальной переменной
        current_output_file = output_file  # Сохранение имени выходного файла в глобальной переменной
        ffmpeg_output = []  # Инициализация списка для накопления строк вывода процесса ffmpeg
        for line in process.stdout:  # Чтение вывода процесса по строкам
            line = line.strip()  # Удаление лишних пробелов в начале и конце строки
            ffmpeg_output.append(line)  # Добавление строки в список вывода для дальнейшего логирования
            match = re.search(r'fps=(\S+)', line)  # Поиск в строке шаблона, указывающего на значение fps
            if match:
                fps_str = match.group(1)  # Извлечение строки с числовым значением fps
                try:
                    fps_val = float(fps_str)  # Преобразование строки в число с плавающей точкой
                    root.after(0, update_fps_label, f"{fps_val:.2f}")  # Обновление метки скорости в интерфейсе, форматируя fps до двух знаков после запятой
                    if (total_frames_holder["value"] is not None) and (fps_val > 0):  # Если общее число кадров известно и скорость больше нуля
                        remaining_frames = total_frames_holder["value"] - last_frame  # Вычисление оставшегося количества кадров
                        estimated_time = round(remaining_frames / fps_val)  # Расчет примерного оставшегося времени конвертации
                        root.after(0, update_estimated_time_label, estimated_time)  # Обновление метки с оценочным временем в интерфейсе
                except Exception:
                    pass  # В случае ошибки преобразования значения fps игнорируем исключение
            if line.startswith("frame="):  # Если строка начинается с 'frame=', она содержит информацию о количестве обработанных кадров
                try:
                    frames_str = line[len("frame="):].strip().split()[0]  # Извлечение числа кадров из строки
                    last_frame = int(frames_str)  # Преобразование извлеченной строки в целое число и обновление переменной last_frame
                    if total_frames_holder["value"] is None:  # Если общее число кадров еще не получено
                        root.after(0, update_total_frames_label, last_frame, "N/A")  # Обновление метки с текущим числом кадров и отсутствующим общим числом
                    else:
                        root.after(0, update_total_frames_label, last_frame, total_frames_holder["value"])  # Обновление метки с текущим и общим числом кадров
                        progress = (last_frame / total_frames_holder["value"]) * 100  # Вычисление процента выполненной конвертации для текущего файла
                    if progress > 100:  # Если процент прогресса превышает 100
                        progress = 100  # Ограничение прогресса значением 100
                    root.after(0, update_file_progress, progress)  # Обновление графического индикатора прогресса в интерфейсе
                except Exception:
                    pass  # Игнорирование ошибки при обновлении прогресса кадров
        # Если процесс ffprobe все еще активен, завершаем его
        if ffprobe_process is not None and ffprobe_process.poll() is None:  # Проверка, выполняется ли процесс ffprobe
            try:
                ffprobe_process.terminate()  # Попытка завершения процесса ffprobe
                logger.info("Завершаем процесс ffprobe, так как конвертация завершена.")  # Логирование завершения процесса ffprobe
            except Exception as e:
                logger.error(f"Ошибка при завершении процесса ffprobe: {e}")  # Логирование ошибки при завершении процесса ffprobe
        process.wait()  # Ожидание завершения процесса конвертации ffmpeg
        # Сброс метки общего количества кадров после завершения конвертации
        root.after(0, update_total_frames_label, "N/A", "N/A")  # Обновление метки, указывающей, что данные недоступны
        current_conversion_process = None  # Обнуление переменной процесса конвертации
        current_output_file = None  # Обнуление переменной выходного файла
        root.after(0, update_file_progress, 100)  # Обновление прогресс-бара текущего файла до 100%
        if process.returncode == 0:  # Если процесс завершился успешно (код возврата 0)
            logger.info(f"Конвертация успешно завершена: {file_path} -> {output_file}")  # Логирование успешного завершения конвертации с указанием исходного и выходного файлов
            if should_delete_source:  # Если установлена опция удаления исходного файла
                try:
                    os.remove(file_path)  # Попытка удалить исходный файл
                    logger.info(f"Исходный файл удален: {file_path}")  # Логирование успешного удаления исходного файла
                except Exception as ex:
                    logger.error(f"Не удалось удалить файл {file_path}: {ex}")  # Логирование ошибки при удалении файла
                    log_failed_delete(file_path)  # Вызов функции регистрации неудачного удаления файла
        else:
            logger.error(f"Ошибка конвертации файла {file_path}. Код возврата: {process.returncode}\nВывод ffmpeg:\n{chr(10).join(ffmpeg_output)}")  # Логирование ошибки конвертации с выводом кода возврата и лога ffmpeg
    except Exception as ex:
        logger.error(f"Исключение при конвертации файла {file_path}: {ex}")  # Логирование исключения, возникшего при запуске конвертации


def truncate_filename(filename, max_length=30):  # Функция для усечения длинных имен файлов, если они превышают заданную длину
    if len(filename) > max_length:  # Если длина имени файла превышает max_length
        return "..." + filename[-(max_length-3):]  # Возвращается усеченное имя файла с ведущими многоточиями
    return filename  # Если имя файла не превышает max_length, возвращается оно без изменений


def disable_settings():  # Функция для отключения (деактивации) элементов интерфейса во время выполнения конвертации
    folder_entry.config(state="disabled", disabledbackground="#3c3c3c", disabledforeground="#d4d4d4")  # Деактивация поля ввода папки с изменением цвета фона и текста
    folder_button.config(state="disabled", bg="#3c3c3c")  # Деактивация кнопки выбора папки
    preset_entry.config(state="disabled", disabledbackground="#3c3c3c", disabledforeground="#d4d4d4")  # Деактивация поля ввода параметра preset
    crf_entry.config(state="disabled", disabledbackground="#3c3c3c", disabledforeground="#d4d4d4")  # Деактивация поля ввода параметра CRF
    height_entry.config(state="disabled", disabledbackground="#3c3c3c", disabledforeground="#d4d4d4")  # Деактивация поля ввода фильтра по высоте
    delete_check.config(state="disabled", disabledforeground="#d4d4d4")  # Деактивация чекбокса удаления исходных файлов с изменением цвета текста
    start_button.config(state="disabled", bg="#3c3c3c")  # Деактивация кнопки запуска конвертации


def enable_settings():  # Функция для включения (активации) элементов интерфейса после завершения конвертации
    folder_entry.config(state="normal")  # Активация поля ввода папки
    folder_button.config(state="normal", bg="#0e639c")  # Активация кнопки выбора папки
    preset_entry.config(state="normal")  # Активация поля ввода preset
    crf_entry.config(state="normal")  # Активация поля ввода CRF
    height_entry.config(state="normal")  # Активация поля ввода фильтра по высоте
    delete_check.config(state="normal")  # Активация чекбокса удаления исходных файлов
    start_button.config(state="normal", bg="#0e639c")  # Активация кнопки запуска конвертации


def start_conversion_thread(folder, preset, crf, height_filter, should_delete_source, status_label):  # Функция запуска конвертации для всех видеофайлов в выбранной папке с фильтрацией по высоте
    """
    Запуск конвертации для всех файлов в указанной папке с фильтрацией по минимальной высотой видео.
    Дополнительно отсекаются файлы, уже сконвертированные ранее (имя заканчивается на '_av1'),
    файлы с размером менее 3 килобайт и в процессе фильтрации обновляется статус.
    """
    global conversion_finished, stop_requested  # Объявление глобальных переменных для контроля процесса конвертации
    logger.info(f"Запуск конвертации для папки: {folder}")  # Логирование начала конвертации для выбранной папки
    allowed_exts = ('.mp4', '.avi', '.mkv', '.webm', '.m4v', '.flv')  # Определяются допустимые расширения видеофайлов
    video_files = []  # Инициализируется список для хранения найденных видеофайлов
    for dir_path, dirs, files in os.walk(folder):  # Рекурсивный обход всех подкаталогов выбранной папки
        for filename in files:  # Перебор каждого файла в текущем каталоге
            if filename.lower().endswith(allowed_exts):  # Проверка, соответствует ли файл одному из допустимых расширений
                full_path = os.path.join(dir_path, filename)  # Формирование полного пути к файлу
                base_name, file_ext = os.path.splitext(filename)  # Разделение имени файла на базовую часть и расширение
                if base_name.endswith("_av1"):  # Пропуск файлов, которые уже сконвертированы (оканчиваются на '_av1')
                    continue
                converted_file = os.path.join(dir_path, base_name + "_av1" + file_ext)  # Формирование предполагаемого имени сконвертированного файла
                if os.path.exists(converted_file):  # Если конвертированный файл уже существует
                    if should_delete_source:  # Если включена опция удаления исходного файла
                        try:
                            os.remove(full_path)  # Попытка удалить исходный файл
                            logger.info(f"Исходный файл {full_path} удалён, так как уже существует конвертированный {converted_file}")  # Логирование успешного удаления
                        except Exception as ex:
                            logger.error(f"Ошибка удаления файла {full_path}: {ex}")  # Логирование ошибки при удалении файла
                    else:
                        logger.info(f"Файл {full_path} пропущен, так как уже существует конвертированный {converted_file}")  # Логирование пропуска файла
                    continue  # Переход к следующему файлу
                try:
                    if os.path.getsize(full_path) < 3000:  # Проверка: если размер файла меньше 3 килобайт
                        continue  # Пропуск малых файлов
                except Exception as e:
                    logger.error(f"Ошибка при получении размера файла {full_path}: {e}")  # Логирование ошибки получения размера файла
                    continue
                video_files.append(full_path)  # Добавление файла в список для конвертации
    total_found = len(video_files)  # Определение общего количества найденных видеофайлов
    logger.info(f"Найдено {total_found} видео файлов в папке {folder}")  # Логирование количества найденных файлов
    logger.debug(f"Список видео файлов в папке: {video_files}")  # Логирование списка найденных файлов для отладки
    
    selected_files = []  # Инициализация списка файлов, отобранных для конвертации после фильтрации по высоте
    checked_files = 0  # Счетчик проверенных файлов при фильтрации
    for video_file in video_files:  # Перебор каждого файла из списка найденных видео
        if stop_requested:
            logger.info("Остановка фильтрации файлов по запросу пользователя.")
            break
        checked_files += 1  # Увеличение счетчика проверенных файлов
        root.after(0, partial(status_label.config, text=f"Проверка файлов: {checked_files}/{total_found}"))  # Обновление статуса в интерфейсе
        height = get_video_height(video_file)  # Получение высоты видео для текущего файла
        if height is None:
            logger.warning(f"Файл {video_file} пропущен (невозможно определить высоту)")
            continue
        if height < height_filter:
            logger.info(f"Файл {video_file} пропущен: высота {height} меньше заданного {height_filter}")
        else:
            selected_files.append(video_file)
    total_files = len(selected_files)  # Определение общего количества файлов после фильтрации
    logger.info(f"Для конвертации отобрано {total_files} файлов")  # Логирование количества файлов, отобранных для конвертации
    logger.debug(f"Список файлов для конвертации после фильтра: {selected_files}")  # Логирование списка отобранных файлов для отладки
    
    original_total = 0  # Инициализация переменной для суммарного размера исходных файлов (в байтах)
    converted_total = 0  # Инициализация переменной для суммарного размера конвертированных файлов (в байтах)

    root.after(0, partial(files_count_label.config, text=f"Количество файлов: 0/{total_files}"))  # Обновление метки количества файлов в интерфейсе с начальным значением
    for i, source_file in enumerate(selected_files):  # Перебор отобранных файлов с индексом
        if stop_requested:  # Если запрошена остановка конвертации
            status_label.config(text="Конвертация отменена.")  # Обновление статуса в интерфейсе, показывающее отмену
            logger.info("Конвертация отменена пользователем.")  # Логирование отмены конвертации пользователем
            break  # Прерывание цикла обработки файлов

        status_label.config(text=f"Конвертация: {truncate_filename(os.path.basename(source_file))}")  # Обновление статуса в интерфейсе с именем текущего файла (усеченным, если слишком длинное)
        
        try:
            orig_size = os.path.getsize(source_file)  # Определение размера исходного файла
        except Exception:
            orig_size = 0  # В случае ошибки размер считается равным 0
        original_total += orig_size  # Добавление размера текущего исходного файла к общему размеру
        
        convert_file(source_file, preset, crf, should_delete_source)  # Запуск конвертации текущего файла
        
        base, ext = os.path.splitext(source_file)  # Разделение пути исходного файла на базовое имя и расширение
        output_file = base + "_av1" + ext  # Формирование имени выходного файла с добавлением суффикса
        conv_size = 0  # Инициализация переменной для размера конвертированного файла
        if os.path.exists(output_file):  # Проверка существования конвертированного файла
            try:
                conv_size = os.path.getsize(output_file)  # Определение размера конвертированного файла
            except Exception:
                conv_size = 0  # В случае ошибки размер считается равным 0
        converted_total += conv_size  # Добавление размера конвертированного файла к общему размеру
        
        overall = ((i + 1) / total_files) * 100  # Вычисление общего процента завершения конвертации по всем файлам
        root.after(0, update_overall_progress, overall)  # Обновление общего прогресс-бара в интерфейсе
        root.after(0, partial(files_count_label.config, text=f"Количество файлов: {i+1}/{total_files}"))  # Обновление метки с количеством обработанных файлов
    
    conversion_finished = True  # Установка флага завершения конвертации
    if not stop_requested:  # Если конвертация не была отменена
        logger.info("Все файлы обработаны.")  # Логирование завершения обработки всех файлов
        space_saved = original_total - converted_total  # Вычисление сэкономленного места в байтах
        if original_total > 0:
            percent_saved = (space_saved / original_total) * 100  # Вычисление процента сэкономленного места
        else:
            percent_saved = 0  # Если исходный размер равен 0, процент сбережений устанавливается в 0
        message_text = (f"Конвертация завершена для всех файлов.\n\n"
                        f"Общий размер исходных файлов: {original_total/(1024*1024):.2f} MB\n"
                        f"Общий размер сконвертированных файлов: {converted_total/(1024*1024):.2f} MB\n"
                        f"Сэкономлено: {space_saved/(1024*1024):.2f} MB ({percent_saved:.2f}%)\n")  # Формирование итогового сообщения с результатами конвертации
        logger.info(message_text)  # Логирование итогового сообщения с результатами
        messagebox.showinfo("Готово", message_text)  # Отображение итогового сообщения пользователю с помощью диалогового окна
    
    if stop_requested:
        status_label.config(text="Конвертация остановлена.")
        logger.info("Конвертация остановлена пользователем во время фильтрации файлов.")
        root.after(0, enable_settings)
        root.after(0, finalize_failed_deletions_file)
        return
    
    root.after(0, enable_settings)  # Восстановление активности элементов интерфейса после завершения конвертации
    root.after(0, finalize_failed_deletions_file)  # Вызов функции завершения файла failed_deletions.cmd


def browse_folder():  # Функция для выбора папки с видеофайлами через диалоговое окно
    folder = filedialog.askdirectory(title="Выберите папку с видео")  # Открытие диалога выбора директории с заголовком
    if folder:  # Если пользователь выбрал папку
        folder_entry.delete(0, tk.END)  # Очистка поля ввода папки
        folder_entry.insert(0, folder)  # Вставка выбранного пути в поле ввода
        try:
            allowed_exts = ('.mp4', '.avi', '.mkv', '.webm', '.m4v', '.flv')  # Определение допустимых расширений видеофайлов
            video_files = [os.path.join(dir_path, filename) for dir_path, _, files in os.walk(folder)
                           for filename in files if filename.lower().endswith(allowed_exts)]  # Формирование списка видеофайлов, соответствующих допустимым расширениям
            logger.info(f"Пользователь выбрал папку: {folder} с {len(video_files)} подходящими видеофайлами")  # Логирование выбора папки и количества найденных файлов
            logger.debug(f"Список видео файлов в выбранной папке: {video_files}")  # Логирование списка найденных видеофайлов для отладки
        except Exception as e:
            logger.error(f"Ошибка при получении списка файлов для папки {folder}: {e}")  # Логирование ошибки при получении списка файлов


def start_conversion_gui():  # Функция, вызываемая при нажатии кнопки запуска конвертации через графический интерфейс
    folder = folder_entry.get()  # Получение текста из поля ввода папки
    if not folder or not os.path.isdir(folder):  # Проверка корректности выбранной папки
        messagebox.showerror("Ошибка", "Укажите корректную папку с видео файлами.")  # Отображение сообщения об ошибке, если папка некорректна
        return  # Завершение функции при ошибке
    try:
        preset_value = int(preset_entry.get())  # Преобразование введенного значения preset в целое число
        crf_value = int(crf_entry.get())  # Преобразование введенного значения CRF в целое число
        height_filter = int(height_entry.get())  # Преобразование введенного значения фильтра по высоте в целое число
    except ValueError:
        messagebox.showerror("Ошибка", "Параметры конвертации и фильтра должны быть целыми числами.")  # Отображение сообщения об ошибке, если преобразование не удалось
        return  # Завершение функции при ошибке преобразования
    should_delete_source = delete_var.get()  # Получение логического значения из чекбокса удаления исходных файлов
    status_label.config(text="Запуск конвертации...")  # Обновление метки статуса, информируя пользователя о начале процесса
    
    disable_settings()  # Отключение элементов интерфейса для предотвращения изменений во время конвертации
    
    global conversion_start_time, conversion_finished  # Объявление глобальных переменных для времени начала и статуса конвертации
    conversion_start_time = time.time()  # Фиксация текущего времени как начала конвертации
    conversion_finished = False  # Сброс флага завершения конвертации для начала процесса
    root.after(0, update_timer)  # Запуск функции обновления таймера конвертации
    threading.Thread(target=start_conversion_thread, args=(folder, preset_value, crf_value, height_filter, should_delete_source, status_label), daemon=True).start()  # Запуск конвертации в отдельном потоке для параллельного выполнения
    logger.info("Пользователь запустил конвертацию.")  # Логирование факта запуска конвертации пользователем


def update_file_progress(value):  # Функция для обновления прогресса конвертации текущего файла в графическом интерфейсе
    file_progress_bar['value'] = value  # Установка значения прогресс-бара для текущего файла
    file_progress_numeric_label.config(text=f"{value:.1f}%")  # Обновление текстовой метки с отображением процента выполнения


def update_overall_progress(value):  # Функция для обновления общего прогресса конвертации по всем файлам
    overall_progress_bar['value'] = value  # Установка значения общего прогресс-бара
    overall_progress_numeric_label.config(text=f"{value:.1f}%")  # Обновление текстовой метки с общим процентом выполнения


def stop_conversion():  # Функция для остановки запущенной конвертации по запросу пользователя
    global stop_requested, current_conversion_process, current_output_file, conversion_finished, timer_id  # Объявление глобальных переменных для контроля процесса остановки
    stop_requested = True  # Установка флага запроса остановки конвертации
    if current_conversion_process:  # Если существует активный процесс конвертации
        try:
            current_conversion_process.kill()  # Попытка принудительно остановить процесс конвертации
            logger.info("Процесс конвертации остановлен.")  # Логирование успешной остановки процесса
        except Exception as ex:
            logger.error(f"Ошибка при остановке процесса: {ex}")  # Логирование ошибки, возникшей при остановке процесса
    if current_output_file and os.path.exists(current_output_file):  # Если существует выходной файл незавершенной конвертации
        try:
            os.remove(current_output_file)  # Попытка удаления незавершенного файла
            logger.info(f"Незавершенный файл удален: {current_output_file}")  # Логирование успешного удаления незавершенного файла
        except Exception as ex:
            logger.error(f"Не удалось удалить незавершенный файл: {ex}")  # Логирование ошибки удаления незавершенного файла
            log_failed_delete(current_output_file)  # Вызов функции для регистрации неудачного удаления
    current_conversion_process = None  # Обнуление переменной текущего процесса конвертации
    current_output_file = None  # Обнуление переменной текущего выходного файла
    status_label.config(text="Конвертация остановлена.")  # Обновление метки статуса, сообщая о остановке конвертации
    folder_entry.delete(0, tk.END)  # Очистка поля ввода папки
    conversion_finished = True  # Установка флага завершения конвертации для остановки таймера
    if timer_id is not None:  # Если существует активный таймер
        root.after_cancel(timer_id)  # Отмена запланированного обновления таймера
        timer_id = None  # Обнуление идентификатора таймера
    # Сброс значений полей "Время конвертации" и "Количество файлов"
    timer_label.config(text="Время: 0.0 сек")
    files_count_label.config(text="Количество файлов: N/A")
    root.after(0, enable_settings)  # Включение элементов интерфейса после остановки конвертации
    root.after(0, finalize_failed_deletions_file)  # Вызов функции завершения файла failed_deletions.cmd


def update_timer():  # Функция обновления таймера, показывающая время, прошедшее с начала конвертации
    global conversion_start_time, conversion_finished, timer_id  # Объявление глобальных переменных для времени старта и статуса конвертации
    elapsed = time.time() - conversion_start_time  # Вычисление прошедшего времени с момента старта конвертации
    timer_label.config(text=f"Время конвертации: {elapsed:.1f} сек")  # Обновление метки таймера с отображением прошедшего времени
    if not conversion_finished:  # Если конвертация еще не завершена
        timer_id = root.after(100, update_timer)  # Планирование обновления функции через 100 миллисекунд


def update_fps_label(fps_value):  # Функция обновления метки, отображающей скорость конвертации в fps
    fps_label.config(text=f"Скорость конвертации: {fps_value} fps")  # Обновление текста метки с текущим значением fps


def log_failed_delete(file_path):  # Функция для записи команды удаления файла в файл failed_deletions.cmd в случае неудачи удаления
    """
    Записывает команду удаления файла в формате CMD в файл failed_deletions.cmd,
    который находится в папке logs. Если файл не существует, сначала записывается 'chcp 65001'.
    """
    try:
        log_dir = "logs"  # Задается директория, где хранится файл failed_deletions.cmd
        failed_deletions_file = os.path.join(log_dir, "failed_deletions.cmd")  # Формируется путь к файлу failed_deletions.cmd
        norm_path = os.path.normpath(file_path)  # Приведение пути к файлу к корректному формату Windows
        if not os.path.exists(failed_deletions_file):  # Если файл failed_deletions.cmd еще не существует
            with open(failed_deletions_file, "w", encoding="utf-8") as f:  # Создание нового файла с кодировкой UTF-8
                f.write("chcp 65001\n")  # Запись команды смены кодировки в файл
        with open(failed_deletions_file, "a", encoding="utf-8") as f:  # Открытие файла в режиме добавления
            f.write(f'del /F /Q "{norm_path}"\n')  # Запись команды удаления файла в формате CMD
        logger.info(f"Добавлена команда удаления в файл: {failed_deletions_file} для файла {norm_path}")  # Логирование добавления команды удаления в файл
    except Exception as ex:
        logger.error(f"Не удалось записать в файл failed_deletions.cmd: {ex}")  # Логирование ошибки записи в файл failed_deletions.cmd


def finalize_failed_deletions_file():  # Функция завершения файла failed_deletions.cmd, дописывающая команду pause
    """
    Дописывает в конец файла failed_deletions.cmd команду 'pause', если файл существует.
    """
    try:
        log_dir = "logs"  # Задается директория логов
        failed_deletions_file = os.path.join(log_dir, "failed_deletions.cmd")  # Формируется путь к файлу failed_deletions.cmd
        if os.path.exists(failed_deletions_file):  # Если файл существует
            with open(failed_deletions_file, "a", encoding="utf-8") as f:  # Открытие файла в режиме добавления
                f.write("pause\n")  # Дописывание команды pause в конец файла
            logger.info(f"Файл {failed_deletions_file} завершен командой pause.")  # Логирование успешного завершения файла
    except Exception as ex:
        logger.error(f"Не удалось завершить файл failed_deletions.cmd: {ex}")  # Логирование ошибки при завершении файла


# --- Создание GUI ---  # Начало создания графического интерфейса пользователя
root = tk.Tk()  # Создание главного окна приложения
root.title("Конвертер видео в формат AV1")  # Установка заголовка главного окна

# Настройка темной темы, имитирующей палитру VS Code
root.configure(bg="#1e1e1e")  # Установка темного фона для главного окна

style = ttk.Style(root)  # Создание объекта стиля для ttk виджетов
style.theme_use("clam")  # Применение темы "clam" для ttk виджетов

# Настройка виджетов ttk в темной палитре
style.configure("TLabel", background="#1e1e1e", foreground="#d4d4d4")  # Настройка меток: темный фон и светлый текст
style.configure("TButton", background="#0e639c", foreground="#ffffff", relief="flat")  # Настройка кнопок с синим фоном, белым текстом и плоским стилем
style.map("TButton", background=[("active", "#1177bb"), ("disabled", "#3c3c3c")], foreground=[("disabled", "#666666")])  # Настройка цветов кнопок в активном и неактивном состояниях
style.configure("TEntry", fieldbackground="#3c3c3c", foreground="#d4d4d4")  # Настройка полей ввода: темное поле и светлый текст
style.configure("TCheckbutton", background="#1e1e1e", foreground="#d4d4d4")  # Настройка чекбоксов: темный фон и светлый текст

# Поле для ввода папки с видео
tk.Label(root, text="Папка с видео:", bg="#1e1e1e", fg="#d4d4d4").grid(row=0, column=0, padx=5, pady=5, sticky="w")  # Создание и размещение метки для поля ввода папки с видео
folder_entry = tk.Entry(root, width=60, bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4")  # Создание поля ввода для пути к папке с видео
folder_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="w")  # Размещение поля ввода на сетке
folder_button = tk.Button(root, text="Обзор", command=browse_folder, bg="#0e639c", fg="#ffffff", activebackground="#1177bb", activeforeground="#ffffff")  # Создание кнопки для открытия диалога выбора папки
folder_button.grid(row=0, column=3, padx=5, pady=5)  # Размещение кнопки на сетке

# Параметры конвертации: preset, CRF, фильтр по высоте и опция удаления
tk.Label(root, text="Параметр сжатия (preset):", bg="#1e1e1e", fg="#d4d4d4").grid(row=1, column=0, padx=5, pady=5, sticky="w")  # Создание и размещение метки для параметра preset
preset_entry = tk.Entry(root, width=3, bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4")  # Создание поля ввода для параметра preset
preset_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")  # Размещение поля ввода на сетке
preset_entry.insert(0, "7")  # Установка значения по умолчанию для параметра preset

tk.Label(root, text="Фильтр по высоте (пикселей):", bg="#1e1e1e", fg="#d4d4d4").grid(row=1, column=2, padx=2, pady=5, sticky="w")  # Создание и размещение метки для фильтра по высоте
height_entry = tk.Entry(root, width=5, bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4")  # Создание поля ввода для фильтра по высоте
height_entry.grid(row=1, column=3, padx=2, pady=5, sticky="w")  # Размещение поля ввода на сетке
height_entry.insert(0, "720")  # Установка значения по умолчанию для фильтра по высоте

tk.Label(root, text="Параметр качества (CRF):", bg="#1e1e1e", fg="#d4d4d4").grid(row=2, column=0, padx=5, pady=5, sticky="w")  # Создание и размещение метки для параметра CRF
crf_entry = tk.Entry(root, width=3, bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4")  # Создание поля ввода для параметра CRF
crf_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")  # Размещение поля ввода на сетке
crf_entry.insert(0, "30")  # Установка значения по умолчанию для параметра CRF

delete_var = tk.BooleanVar(value=True)  # Создание логической переменной для чекбокса удаления исходных файлов, по умолчанию True
delete_check = tk.Checkbutton(root, text="Удалять исходные файлы", variable=delete_var, bg="#1e1e1e", fg="#d4d4d4", selectcolor="#1e1e1e")  # Создание чекбокса для выбора удаления исходных файлов
delete_check.grid(row=2, column=2, padx=5, pady=5, sticky="w")  # Размещение чекбокса на сетке

# Добавляем текстовое поле с описанием настроек (меньшим шрифтом)
desc_text = ("Параметр сжатия (preset): влияет на скорость конвертации и качество. 1-12. Больше - быстрее, но слабее сжатие.\n"
             "Параметр качества (CRF): определяет компромисс между качеством и размером файла. 1-30. Больше - качественней.\n"
             "Фильтр по высоте (пикселей): исключает видео с высотой ниже указаной. \n"
             "Удалять исходные файлы: удаляет исходный файл после успешной конвертации.")  # Многострочное описание настроек конвертации
description_label = tk.Label(root, text=desc_text, font=(None, 7), wraplength=600, justify="left", anchor="w", bg="#1e1e1e", fg="#d4d4d4")  # Создание метки для отображения описания настроек с мелким шрифтом
description_label.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="w")  # Размещение метки описания настроек на сетке

# Обновляем номера строк для оставшихся элементов
start_button = tk.Button(root, text="Запустить конвертацию", command=start_conversion_gui, bg="#0e639c", fg="#ffffff", activebackground="#1177bb", activeforeground="#ffffff")  # Создание кнопки запуска конвертации
start_button.grid(row=4, column=0, padx=5, pady=5, sticky="w")  # Размещение кнопки запуска на сетке

stop_button = tk.Button(root, text="Отменить конвертацию", command=stop_conversion, bg="#0e639c", fg="#ffffff", activebackground="#1177bb", activeforeground="#ffffff")  # Создание кнопки для остановки конвертации
stop_button.grid(row=4, column=1, padx=5, pady=5, sticky="w")  # Размещение кнопки остановки на сетке

files_count_label = tk.Label(root, text="Количество файлов: N/A", anchor="w", bg="#1e1e1e", fg="#d4d4d4")  # Создание метки для отображения количества файлов для конвертации
files_count_label.grid(row=4, column=2, padx=5, pady=5, sticky="w")  # Размещение метки на сетке

estimated_time_label = tk.Label(root, text="Оценочное время: N/A", anchor="w", bg="#1e1e1e", fg="#d4d4d4")  # Создание метки для отображения оценочного времени конвертации
estimated_time_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")  # Размещение метки с оценочным временем на сетке

fps_label = tk.Label(root, text="Скорость: N/A fps", anchor="w", bg="#1e1e1e", fg="#d4d4d4")  # Создание метки для отображения скорости конвертации (fps)
fps_label.grid(row=5, column=1, padx=5, pady=5, sticky="w")  # Размещение метки скорости на сетке

total_frames_label = tk.Label(root, text="Количество кадров: N/A", anchor="w", bg="#1e1e1e", fg="#d4d4d4")  # Создание метки для отображения общего количества кадров
total_frames_label.grid(row=5, column=2, padx=5, pady=5, sticky="w")  # Размещение метки общего количества кадров на сетке

tk.Label(root, text="Текущий файла:", bg="#1e1e1e", fg="#d4d4d4").grid(row=6, column=0, columnspan=3, padx=5, pady=(5,0), sticky="w")  # Создание метки для отображения текущего обрабатываемого файла
file_progress_bar = ttk.Progressbar(root, orient="horizontal", length=370, mode="determinate")  # Создание прогресс-бара для отображения выполнения конвертации текущего файла
file_progress_bar.grid(row=6, column=1, columnspan=2, padx=5, pady=5, sticky="w")  # Размещение прогресс-бара на сетке
file_progress_numeric_label = tk.Label(root, text="0%", bg="#1e1e1e", fg="#d4d4d4")  # Создание метки для отображения числового значения прогресса текущего файла
file_progress_numeric_label.grid(row=6, column=3, padx=5, pady=5, sticky="w")  # Размещение метки с числовым значением прогресса на сетке

tk.Label(root, text="Общий прогресс:", bg="#1e1e1e", fg="#d4d4d4").grid(row=7, column=0, columnspan=3, padx=5, pady=(5,0), sticky="w")  # Создание метки для отображения общего прогресса конвертации всех файлов
overall_progress_bar = ttk.Progressbar(root, orient="horizontal", length=370, mode="determinate")  # Создание общего прогресс-бара для всех файлов
overall_progress_bar.grid(row=7, column=1, columnspan=2, padx=5, pady=5, sticky="w")  # Размещение общего прогресс-бара на сетке
overall_progress_numeric_label = tk.Label(root, text="0%", bg="#1e1e1e", fg="#d4d4d4")  # Создание метки для отображения числового значения общего прогресса
overall_progress_numeric_label.grid(row=7, column=3, padx=5, pady=5, sticky="w")  # Размещение метки общего прогресса на сетке

status_label = tk.Label(root, text="Ожидание запуска конвертации", anchor="w", width=40, bg="#1e1e1e", fg="#d4d4d4")  # Создание метки статуса, информирующей о текущем состоянии конвертации
status_label.grid(row=8, column=0, columnspan=2, padx=5, pady=5, sticky="we")  # Размещение метки статуса с растяжением по ширине

timer_label = tk.Label(root, text="Время: 0.0 сек", anchor="w", bg="#1e1e1e", fg="#d4d4d4")  # Создание метки для отображения прошедшего времени конвертации
timer_label.grid(row=8, column=2, padx=5, pady=5, sticky="w")  # Размещение метки таймера на сетке

root.grid_columnconfigure(0, minsize=50)  # Настройка минимального размера первой колонки сетки

#root.geometry("720x260")  # Комментарий: установка фиксированного размера окна (если необходимо), сейчас закомментировано

root.mainloop()  # Запуск главного цикла обработки событий графического интерфейса, что обеспечивает работоспособность приложения