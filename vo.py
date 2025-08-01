import os                # Импортируется модуль os для работы с операционной системой и выполнения операций с файлами
import sys               # Импортируется модуль sys для доступа к системным функциям и переменным интерпретатора
import subprocess        # Импортируется модуль subprocess для выполнения внешних команд и запуска процессов
import threading         # Импортируется модуль threading для работы с потоками и параллельного выполнения кода
import time              # Импортируется модуль time для работы со временем, измерения задерзок и отсчетов
import tkinter as tk     # Импортируется библиотека tkinter для создания графического интерфейса
from tkinter import filedialog, messagebox  # Импортируются диалоговые окна для выбора файлов и вывода сообщений пользователю
from tkinter import ttk  # Импортируется ttk для использования расширенных виджетов (например, Progressbar) с улучшенной стилизацией
from loguru import logger  # Импортируется библиотека loguru для ведения логирования и отладки
import datetime  # Импортируется модуль datetime для работы с датой и временем, используется при формировании имени лога
from functools import partial  # Импортируется функция partial для создания частично применяемых функций, упрощающих вызовы
import re                 # Импортируется модуль re для работы с регулярными выражениями и поиска шаблонов
from get_video_len import get_video_len_and_frames # Импортируем модуль для быстрого получения длительности и FPS

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


def update_estimated_time_label(time_sec):  # Функция обновления метки с оценочным временем конвертации
    total_seconds = int(time_sec)  # Преобразуем значение времени в секундах в целое число
    if total_seconds < 60:  # Если общее время меньше 60 секунд
        display = f"{total_seconds}с"  # Формируем строку, отображающую только секунды, с суффиксом 'с'
    elif total_seconds < 3600:  # Если время меньше 3600 секунд (менее часа)
        minutes = total_seconds // 60  # Вычисляем целое число минут
        seconds = total_seconds % 60  # Вычисляем остаток секунд после извлечения минут
        display = f"{minutes:02d} м {seconds:02d} с"  # Форматируем строку, отображающую минуты и секунды в двухзначном формате
    else:  # Если время составляет 3600 секунд и более (один час или более)
        hours = total_seconds // 3600  # Вычисляем количество полных часов
        minutes = (total_seconds % 3600) // 60  # Вычисляем количество оставшихся минут после вычитания часов
        seconds = total_seconds % 60  # Вычисляем оставшиеся секунды после вычитания часов и минут
        display = f"{hours:02d}ч {minutes:02d}м {seconds:02d}с"  # Форматируем строку, отображающую часы, минуты и секунды в двухзначном формате
    estimated_time_label.config(text=f"Оценочное время: {display}")  # Обновляем метку интерфейса, выводя сформированное оценочное время


def update_total_frames_label(current, total):  # Функция обновления метки, показывающей текущее и общее количество кадров
    total_frames_label.config(text=f"Количество кадров: {current}/{total}")  # Установка нового текста метки с информацией о количестве обработанных и общих кадрах


def convert_file(file_path, preset, crf, should_delete_source, encoder):  # Функция для конвертации одного видеофайла с помощью ffmpeg и кодека libsvtav1
    """
    Конвертация одного файла через ffmpeg с использованием libsvtav1.
    Выходной файл сохраняется в той же директории с добавлением суффикса '_av1'.
    Запуск конвертации происходит сразу, а получение общего количества кадров
    выполняется в отдельном потоке. Пока общее число кадров не получено, прогресс остается 0.
    Обновляются только fps и количество обработанных кадров.
    """
    base, ext = os.path.splitext(file_path)  # Разделение пути на базовое имя и расширение файла
    
    # Определяем желаемый суффикс на основе выбранного кодека
    desired_suffix = "_av1"
    if encoder == "libx264":
        desired_suffix = "_x264"
    
    # Очищаем базовое имя от предыдущих суффиксов (_av1 или _x264), если они есть,
    # чтобы избежать двойных приписок при добавлении нового суффикса.
    cleaned_base = base
    if cleaned_base.endswith("_av1"):
        cleaned_base = cleaned_base[:-len("_av1")]
    elif cleaned_base.endswith("_x264"):
        cleaned_base = cleaned_base[:-len("_x264")]

    output_file = cleaned_base + desired_suffix + ext  # Формирование имени выходного файла с добавлением суффикса
    total_frames_holder: list[int | None] = [None]  # Создание списка для хранения общего количества кадров, полученного в потоке
    last_frame = 0  # Инициализация переменной для хранения последнего обработанного кадра

    # Предварительная оценка общего количества кадров
    initial_total_frames = None
    try:
        video_info = get_video_len_and_frames(videofile=file_path)
        total_frames = video_info.get('total_frames')
        
        if total_frames is not None and total_frames > 0:
            initial_total_frames = total_frames
            total_frames_holder[0] = initial_total_frames # Обновляем хранитель предварительной оценкой
            logger.info(f"Предварительная оценка кадров для {file_path}: {initial_total_frames} (получено через get-video-len)")
        else: # Если total_frames не получен, пробуем рассчитать
            duration = video_info.get('duration')
            avg_fps = video_info.get('frame_rate')
            if duration is not None and avg_fps is not None and avg_fps > 0:
                initial_total_frames = int(duration * avg_fps)
                total_frames_holder[0] = initial_total_frames
                logger.info(f"Предварительная оценка кадров для {file_path}: {initial_total_frames} (на основе {avg_fps:.2f} FPS)")
            elif duration is not None and duration > 0: # Если есть только продолжительность, можно использовать дефолтный FPS
                # Используем стандартные 30 FPS для предварительной оценки, если реальный FPS неизвестен
                initial_total_frames = int(duration * 30)
                total_frames_holder[0] = initial_total_frames
                logger.info(f"Предварительная оценка кадров для {file_path}: {initial_total_frames} (на основе дефолтных 30 FPS)")
    except Exception as ex:
        logger.warning(f"Не удалось получить предварительную оценку кадров для {file_path} с помощью get-video-len: {ex}")

    # Изначально обновляем метку: общее число кадров неизвестно или предварительно оценено
    root.after(0, update_total_frames_label, 0, initial_total_frames if initial_total_frames is not None else "N/A")  # Установка начального состояния метки с информацией о кадрах
    
    cmd = [  # Формирование списка аргументов для команды ffmpeg
        "ffmpeg",             # Имя программы для конвертации видео
        "-y",                 # Параметр для автоматического подтверждения перезаписи выходного файла
        "-i", file_path,      # Указание входного файла
        "-c:v", encoder_var.get(),  # Выбор видеокодека libsvtav1 для конвертации
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
        if process.stdout: # Добавлена проверка, что stdout не None
            for line in process.stdout:  # Чтение вывода процесса по строкам
                line = line.strip()  # Удаление лишних пробелов в начале и конце строки
                ffmpeg_output.append(line)  # Добавление строки в список вывода для дальнейшего логирования
                match = re.search(r'fps=(\S+)', line)  # Поиск в строке шаблона, указывающего на значение fps
                if match:
                    fps_str = match.group(1)  # Извлечение строки с числовым значением fps
                    try:
                        fps_val = float(fps_str)  # Преобразование строки в число с плавающей точкой
                        root.after(0, update_fps_label, f"{fps_val:.2f}")  # Обновление метки скорости в интерфейсе, форматируя fps до двух знаков после запятой
                        if (total_frames_holder[0] is not None) and (fps_val > 0):  # Если общее число кадров известно и скорость больше нуля
                            remaining_frames = total_frames_holder[0] - last_frame  # Вычисление оставшегося количества кадров
                            estimated_time = round(remaining_frames / fps_val)  # Расчет примерного оставшегося времени конвертации
                            root.after(0, update_estimated_time_label, estimated_time)  # Обновление метки с оценочным временем в интерфейсе
                    except Exception:
                        pass  # В случае ошибки преобразования значения fps игнорируем исключение
                if line.startswith("frame="):  # Если строка начинается с 'frame=', она содержит информацию о количестве обработанных кадров
                    try:
                        frames_str = line[len("frame="):].strip().split()[0]  # Извлечение числа кадров из строки
                        last_frame = int(frames_str)  # Преобразование извлеченной строки в целое число и обновление переменной last_frame
                        if total_frames_holder[0] is None:  # Если общее число кадров еще не получено
                            root.after(0, update_total_frames_label, last_frame, "N/A")  # Обновление метки с текущим числом кадров и отсутствующим общим числом
                        else:
                            root.after(0, update_total_frames_label, last_frame, total_frames_holder[0])  # Обновление метки с текущим и общим числом кадров
                            progress = (last_frame / total_frames_holder[0]) * 100  # Вычисление процента выполненной конвертации для текущего файла
                            if progress > 100:  # Если процент прогресса превышает 100
                                progress = 100  # Ограничение прогресса значением 100
                            root.after(0, update_file_progress, progress)  # Обновление графического индикатора прогресса в интерфейсе
                    except Exception:
                        pass  # Игнорирование ошибки при обновлении прогресса кадров
        process.wait()  # Ожидание завершения процесса конвертации ffmpeg
        # Сброс метки общего количества кадров после завершения конвертации
        root.after(0, update_total_frames_label, "N/A", "N/A")  # Обновление метки, указывающей, что данные недоступны
        current_conversion_process = None  # Обнуление переменной процесса конвертации
        current_output_file = None  # Обнуление переменной текущего выходного файла
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

                current_encoder = encoder_var.get()
                target_output_suffix = "_x264" if current_encoder == "libx264" else "_av1"

                # Формируем очищенное базовое имя, убирая _av1 или _x264, если они есть
                cleaned_base_for_check = base_name
                if cleaned_base_for_check.endswith("_av1"):
                    cleaned_base_for_check = cleaned_base_for_check[:-len("_av1")]
                elif cleaned_base_for_check.endswith("_x264"):
                    cleaned_base_for_check = cleaned_base_for_check[:-len("_x264")]
                
                # Формируем имя ожидаемого выходного файла
                expected_output_file = os.path.join(dir_path, cleaned_base_for_check + target_output_suffix + file_ext)

                # Если текущий файл уже имеет целевой суффикс, пропускаем его
                if base_name.endswith(target_output_suffix):
                    logger.info(f"Файл {full_path} пропущен: уже имеет целевой суффикс {target_output_suffix}.")
                    continue

                # Если ожидаемый выходной файл (с целевым суффиксом) уже существует, пропускаем исходный файл
                if os.path.exists(expected_output_file):  # Если конвертированный файл уже существует
                    if should_delete_source:  # Если включена опция удаления исходного файла
                        try:
                            os.remove(full_path)  # Попытка удалить исходный файл
                            logger.info(f"Исходный файл {full_path} удалён, так как уже существует конвертированный {expected_output_file}")  # Логирование успешного удаления
                        except Exception as ex:
                            logger.error(f"Ошибка удаления файла {full_path}: {ex}")  # Логирование ошибки при удалении файла
                    else:
                        logger.info(f"Файл {full_path} пропущен, так как уже существует конвертированный {expected_output_file}")  # Логирование пропуска файла
                    continue  # Переход к следующему файлу
                
                # Проверка размера файла
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
        height = None
        try:
            video_info = get_video_len_and_frames(videofile=video_file)
            height = video_info.get('height')
        except Exception as ex:
            logger.warning(f"Не удалось получить высоту для файла {video_file} с помощью get-video-len: {ex}")

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
        
        convert_file(source_file, preset, crf, should_delete_source, encoder_var.get())  # Запуск конвертации текущего файла
        
        base, ext = os.path.splitext(source_file)  # Разделение пути исходного файла на базовое имя и расширение
        
        # Определяем правильный суффикс на основе выбранного кодека
        current_encoder = encoder_var.get()
        target_suffix = "_x264" if current_encoder == "libx264" else "_av1"
        
        # Очищаем базовое имя от предыдущих суффиксов
        cleaned_base = base
        if cleaned_base.endswith("_av1"):
            cleaned_base = cleaned_base[:-len("_av1")]
        elif cleaned_base.endswith("_x264"):
            cleaned_base = cleaned_base[:-len("_x264")]
        
        output_file = cleaned_base + target_suffix + ext  # Формирование имени выходного файла с правильным суффиксом
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
        root.after(0, lambda: stop_button.config(state="disabled", bg="#3c3c3c"))
        return
    
    root.after(0, enable_settings)  # Восстановление активности элементов интерфейса после завершения конвертации
    root.after(0, finalize_failed_deletions_file)  # Вызов функции завершения файла failed_deletions.cmd
    root.after(0, lambda: stop_button.config(state="disabled", bg="#3c3c3c"))


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


def test_conversion_system():  # Функция тестирования системы конвертации для определения оптимального метода кодирования
    test_video = "test_video/test.mp4"  # Задаем путь к тестовому видеофайлу
    if not os.path.exists(test_video):  # Проверяем, существует ли тестовый видеофайл
        messagebox.showerror("Ошибка", "Тестовое видео не найдено. Поместите файл test_video.mp4 в папку с программой.")  # Выводим сообщение об ошибке, если файл отсутствует
        return  # Прекращаем выполнение функции, так как тестовое видео не найдено
    methods = ["libaom-av1", "librav1e", "libsvtav1", "av1_nvenc", "av1_qsv", "av1_amf", "av1_mf", "av1_vaapi", "libx264"]  # Определяем список методов кодирования для тестирования
    results = {}  # Инициализируем словарь для хранения результатов тестирования для каждого метода
    for method in methods:  # Перебираем каждый метод кодирования из списка
        output_file = f"test_video_{method}.mp4"  # Формируем имя выходного файла для текущего теста конвертации
        cmd = ["ffmpeg", "-y", "-i", test_video, "-c:v", method, "-t", "10", "-progress", "pipe:1", output_file]  # Формируем команду ffmpeg для тестовой конвертации с текущим методом
        logger.info(f"Тест конвертации с {method}: команда: {' '.join(cmd)}")  # Логируем информацию о команде тестирования для данного метода
        try:  # Пытаемся выполнить тестовую конвертацию
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW)  # Запускаем процесс ffmpeg без создания окна консоли
            fps_values = []  # Инициализируем список для хранения значений fps, полученных в ходе теста
            error_occurred = False  # Флаг, указывающий на возникновение ошибки в процессе тестирования; изначально False
            low_speed_timeout = False  # Флаг для определения длительного периода низких fps (<1) во время теста; изначально False
            below_threshold_start = None  # Переменная для фиксации времени начала периода, когда fps оказался ниже 1
            while True:  # Начинаем чтение вывода процесса построчно
                if not proc.stdout: # Добавлена проверка, что stdout не None
                    break
                line = proc.stdout.readline()  # Считываем очередную строку вывода
                if not line:  # Если строка пустая, значит вывод завершен
                    break  # Выходим из цикла чтения, так как вывод исчерпан
                line = line.strip()  # Удаляем лишние пробелы в начале и конце строки
                if "error" in line.lower():  # Если строка содержит слово "error", свидетельствующее об ошибке
                    error_occurred = True  # Устанавливаем флаг ошибки
                    logger.error(f"Ошибка в выводе ffmpeg при тестировании метода {method}: {line}")  # Логируем сообщение об ошибке для данного метода
                    proc.kill()  # Принудительно завершаем процесс ffmpeg
                    break  # Прерываем цикл чтения вывода
                match = re.search(r'fps=(\d+\.?\d*)', line)  # Ищем в строке значение fps с помощью регулярного выражения
                if match:  # Если значение fps найдено в строке
                    try:  # Пытаемся обработать найденное значение fps
                        current_fps = float(match.group(1))  # Преобразуем строку с fps в число с плавающей запятой
                        fps_values.append(current_fps)  # Добавляем текущее значение fps в список
                        current_time = time.time()  # Получаем текущее время для отсчета длительности низкого fps
                        if current_fps < 1:  # Если текущее значение fps меньше 1
                            if below_threshold_start is None:  # Если время начала периода низкого fps еще не зафиксировано
                                below_threshold_start = current_time  # Фиксируем текущее время как начало периода низкого fps
                            elif current_time - below_threshold_start >= 5:  # Если с момента начала низкого fps прошло 5 секунд или более
                                logger.info(f"Метод {method}: fps меньше 1 в течении 5 секунд, тест переключается на следующий.")  # Логируем, что метод не подходит из-за длительного недостатка fps
                                low_speed_timeout = True  # Устанавливаем флаг, указывающий на длительный период низкого fps
                                proc.kill()  # Принудительно завершаем процесс из-за низкой скорости
                                break  # Выходим из цикла чтения вывода
                        else:  # Если текущее значение fps равно или больше 1
                            below_threshold_start = None  # Сбрасываем фиксацию времени низкого fps
                    except Exception:  # Если возникает исключение при обработке значения fps
                        pass  # Игнорируем ошибку и продолжаем чтение вывода
            proc.wait()  # Ожидаем полного завершения процесса ffmpeg
            if error_occurred:  # Если в процессе тестирования произошла ошибка
                results[method] = (True, None)  # Сохраняем результат для метода: ошибка и отсутствующее значение fps
            elif low_speed_timeout:  # Если тест завершился из-за длительного периода низкого fps
                results[method] = (False, 0)  # Сохраняем результат с fps равным 0 для данного метода
            else:  # Если тест прошел без ошибок
                avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0  # Вычисляем среднее значение fps на основе накопленных данных
                results[method] = (False, avg_fps)  # Сохраняем результат для метода: успешное выполнение и среднее значение fps
        except Exception as ex:  # Если при запуске процесса или тестировании возникает исключение
            logger.error(f"Ошибка при тестировании метода {method}: {ex}")  # Логируем возникшее исключение для данного метода
            results[method] = (True, None)  # Сохраняем в результатах информацию о возникшей ошибке
        if os.path.exists(output_file):  # Если тестовый выходной файл был создан
            try:
                os.remove(output_file)  # Пытаемся удалить тестовый выходной файл
            except Exception:
                pass  # Игнорируем ошибку удаления файла
    non_error = {m: data[1] for m, data in results.items() if not data[0]}  # Формируем словарь для методов, где тест прошел без ошибок, с их средним fps
    if non_error:  # Если существуют методы без ошибок
        fastest_method = max(non_error, key=lambda m: non_error[m])  # Определяем метод с максимальным средним fps
        fastest_fps = non_error[fastest_method]  # Получаем среднее значение fps для выбранного метода
    else:  # Если все методы завершились с ошибками
        fastest_method = list(results.keys())[0]  # Выбираем первый метод из словаря результатов по умолчанию
        fastest_fps = 0  # Устанавливаем среднее значение fps равным 0
    encoder_var.set(fastest_method)  # Устанавливаем оптимальный метод кодирования в выпадающем списке интерфейса
    results_text = "\n".join([f"{m}: {'Ошибка' if data[0] else f'{data[1]:.2f} fps'}" for m, data in results.items()])  # Формируем текстовый отчет с результатами тестирования для каждого метода
    messagebox.showinfo("Результат теста", f"Тест завершен.\n\nРезультаты тестирования:\n{results_text}\n\nЛучший метод: {fastest_method} со средней скоростью {fastest_fps:.2f} fps.")  # Отображаем итоговое окно с результатами тестирования для пользователя


def test_conversion():
    threading.Thread(target=test_conversion_system, daemon=True).start()


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
    
    global stop_requested, conversion_start_time, conversion_finished  # Добавляем глобальные переменные
    stop_requested = False  # Сбрасываем флаг остановки, чтобы можно было запустить конвертацию заново

    should_delete_source = delete_var.get()  # Получение логического значения из чекбокса удаления исходных файлов
    status_label.config(text="Запуск конвертации...")  # Обновление метки статуса, информируя пользователя о начале процесса
    
    disable_settings()  # Отключение элементов интерфейса для предотвращения изменений во время конвертации
    stop_button.config(state="normal", bg="#0e639c")
    
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
    stop_button.config(state="disabled", bg="#3c3c3c")


def update_timer():  # Функция обновления таймера, показывающая время конвертации. Обновляет отображение прошедшего времени.
    global timer_id
    if conversion_start_time is None: # Добавлена проверка, что время начала конвертации установлено
        return
    elapsed = time.time() - conversion_start_time  # Вычисляем разницу между текущим временем и временем начала конвертации (в секундах)
    total_seconds = int(elapsed)  # Приводим вычисленное время к целому количеству секунд
    if total_seconds < 60:  # Если прошедшее время меньше 60 секунд
        display = f"{total_seconds}с"  # Формируем строку отображения, показывая время в секундах (например, "15с")
    elif total_seconds < 3600:  # Если прошедшее время меньше одного часа (от 60 до 3599 секунд)
        minutes = total_seconds // 60  # Вычисляем количество полных минут
        seconds = total_seconds % 60  # Вычисляем оставшиеся секунды после вычитания минут
        display = f"{minutes:02d} м {seconds:02d} с"  # Форматируем строку с минутами и секундами с ведущими нулями (например, "05 м 30 с")
    else:  # Если прошедшее время составляет один час или более (от 3600 секунд и выше)
        hours = total_seconds // 3600  # Вычисляем количество полных часов
        minutes = (total_seconds % 3600) // 60  # Вычисляем количество минут, оставшихся после вычитания часов
        seconds = total_seconds % 60  # Вычисляем оставшиеся секунды после вычитания часов и минут
        display = f"{hours:02d}ч {minutes:02d}м {seconds:02d}с"  # Форматируем строку с часами, минутами и секундами (например, "01ч 22м 01с")
    timer_label.config(text=f"Время конвертации: {display}")  # Обновляем текст метки таймера в интерфейсе, выводя отформатированное время конвертации
    if not conversion_finished:  # Если процесс конвертации ещё не завершён
        timer_id = root.after(100, update_timer)  # Планируем повторный вызов функции update_timer через 100 миллисекунд для обновления отображения времени


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


def finalize_failed_deletions_file():  # Функция завершения файла failed_deletions.cmd, дописывающая команду pause, если её там еще нет
    """
    Дописывает в конец файла failed_deletions.cmd команду 'pause' единожды, если файл существует и если последняя непустая строка не 'pause'.
    """
    try:
        log_dir = "logs"  # Задается директория логов
        failed_deletions_file = os.path.join(log_dir, "failed_deletions.cmd")  # Формируется путь к файлу failed_deletions.cmd
        if os.path.exists(failed_deletions_file):  # Если файл существует
            with open(failed_deletions_file, "r", encoding="utf-8") as f:  # Открываем файл для чтения
                lines = f.readlines()  # Чтение всех строк файла
            last_nonempty = None  # Инициализация переменной для хранения последней непустой строки
            for line in reversed(lines):  # Проход по строкам в обратном порядке
                if line.strip():  # Если строка не пустая
                    last_nonempty = line.strip()  # Запоминаем последнюю непустую строку
                    break
            if last_nonempty != "pause":  # Если последняя непустая строка не 'pause'
                with open(failed_deletions_file, "a", encoding="utf-8") as f:  # Открытие файла в режиме добавления
                    f.write("pause\n")  # Дописывание команды pause в конец файла
                logger.info(f"Файл {failed_deletions_file} завершен командой pause.")  # Логирование завершения файла
            else:
                logger.info(f"Файл {failed_deletions_file} уже содержит команду pause.")  # Логирование, что команда уже записана
    except Exception as ex:
        logger.error(f"Не удалось завершить файл failed_deletions.cmd: {ex}")  # Логирование ошибки при завершении файла


# --- Создание GUI ---  # Начало создания графического интерфейса пользователя
root = tk.Tk()  # Создание главного окна приложения
root.title("Конвертер видео в формат AV1")  # Установка заголовка главного окна

# Настройка темной темы, имитирующей палитру VS Code
root.configure(bg="#1e1e1e")  # Установка темного фона для главного окна

style = ttk.Style(root)  # Создание объекта стиля для ttk виджетов
style.theme_use("clam")  # Применение темы "clam" для ttk виджетов
style.configure("Horizontal.TProgressbar", troughcolor="#bab5ab", background="#0e639c")  # Настройка прогрессбара: серый фон, синий индикатор

# Новые элементы в строке 0: кнопка "Тест" и выпадающий список для выбора кодера (депокеда)
test_button = tk.Button(root, text="Тест", command=test_conversion, bg="#0e639c", fg="#ffffff", activebackground="#1177bb", activeforeground="#ffffff", width=20)
test_button.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="w")
tk.Label(root, text="Кодек:", bg="#1e1e1e", fg="#d4d4d4").grid(row=0, column=1, padx=5, pady=5, sticky="w")
encoder_options = ["libaom-av1", "libsvtav1", "librav1e", "av1_qsv", "av1_nvenc", "av1_amf", "av1_mf", "av1_vaapi", "libx264"]
encoder_var = tk.StringVar(value=encoder_options[0])
encoder_dropdown = tk.OptionMenu(root, encoder_var, *encoder_options)
encoder_dropdown.config(bg="#3c3c3c", fg="#d4d4d4", activebackground="#0e639c", activeforeground="#ffffff")
encoder_dropdown["menu"].config(bg="#3c3c3c", fg="#d4d4d4", activebackground="#0e639c", activeforeground="#ffffff")
encoder_dropdown.grid(row=0, column=2, padx=5, pady=5, sticky="w")

# Перенос элементов выбора папки с видео из строки 0 в строку 4.
tk.Label(root, text="Папка с видео:", bg="#1e1e1e", fg="#d4d4d4").grid(row=4, column=0, padx=5, pady=5, sticky="w")
folder_entry = tk.Entry(root, width=60, bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4")
folder_entry.grid(row=4, column=1, columnspan=2, padx=5, pady=5, sticky="w")
folder_button = tk.Button(root, text="Обзор", command=browse_folder, bg="#0e639c", fg="#ffffff", activebackground="#1177bb", activeforeground="#ffffff")
folder_button.grid(row=4, column=3, padx=5, pady=5)

# Груз параметров конвертации (preset и фильтр по высоте) остаются в строке 1
tk.Label(root, text="Параметр сжатия (preset):", bg="#1e1e1e", fg="#d4d4d4").grid(row=1, column=0, padx=5, pady=5, sticky="w")
preset_entry = tk.Entry(root, width=3, bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4")
preset_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
preset_entry.insert(0, "7")
tk.Label(root, text="Фильтр по высоте (пикселей):", bg="#1e1e1e", fg="#d4d4d4").grid(row=1, column=2, padx=2, pady=5, sticky="w")
height_entry = tk.Entry(root, width=5, bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4")
height_entry.grid(row=1, column=3, padx=2, pady=5, sticky="w")
height_entry.insert(0, "720")
tk.Label(root, text="Параметр качества (CRF):", bg="#1e1e1e", fg="#d4d4d4").grid(row=2, column=0, padx=5, pady=5, sticky="w")
crf_entry = tk.Entry(root, width=3, bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4")
crf_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
crf_entry.insert(0, "30")
delete_var = tk.BooleanVar(value=True)  # Создание логической переменной для чекбокса удаления исходных файлов, по умолчанию True
delete_check = tk.Checkbutton(root, text="Удалять исходные файлы", variable=delete_var, bg="#1e1e1e", fg="#d4d4d4", selectcolor="#1e1e1e")
delete_check.grid(row=2, column=2, padx=5, pady=5, sticky="w")

# Текстовое описание настроек (строка 3)
desc_text = ("Параметр сжатия (preset): влияет на скорость конвертации и размер. 1-12. Больше - быстрее, но слабее сжатие.\n"
             "Параметр качества (CRF): определяет компромисс между качеством и размером файла. 1-40. Больше - качественней.\n"
             "Фильтр по высоте (пикселей): исключает видео с высотой ниже указаной. \n"
             "Удалять исходные файлы: удаляет исходный файл после успешной конвертации.")
description_label = tk.Label(root, text=desc_text, font=("", 7), wraplength=600, justify="left", anchor="w", bg="#1e1e1e", fg="#d4d4d4")
description_label.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="w")

# Кнопки запуска и остановки конвертации, а также метка количества файлов – перемещаются с row 4 на row 5
start_button = tk.Button(root, text="Запустить конвертацию", command=start_conversion_gui, bg="#0e639c", fg="#ffffff", activebackground="#1177bb", activeforeground="#ffffff")
start_button.grid(row=5, column=0, padx=5, pady=5, sticky="w")
stop_button = tk.Button(root, text="Отменить конвертацию", command=stop_conversion, bg="#3c3c3c", fg="#ffffff", activebackground="#1177bb", activeforeground="#ffffff", state="disabled")
stop_button.grid(row=5, column=1, padx=5, pady=5, sticky="w")
files_count_label = tk.Label(root, text="Количество файлов: N/A", anchor="w", bg="#1e1e1e", fg="#d4d4d4")
files_count_label.grid(row=5, column=2, padx=5, pady=5, sticky="w")

# Метки оценки оставшегося времени, скорости и количества кадров – переиндексированы: row 5 -> row 6
estimated_time_label = tk.Label(root, text="Оценочное время: N/A", anchor="w", bg="#1e1e1e", fg="#d4d4d4")
estimated_time_label.grid(row=6, column=0, padx=5, pady=5, sticky="w")
fps_label = tk.Label(root, text="Скорость: N/A fps", anchor="w", bg="#1e1e1e", fg="#d4d4d4")
fps_label.grid(row=6, column=1, padx=5, pady=5, sticky="w")
total_frames_label = tk.Label(root, text="Количество кадров: N/A", anchor="w", bg="#1e1e1e", fg="#d4d4d4")
total_frames_label.grid(row=6, column=2, padx=5, pady=5, sticky="w")

# Метки для текущего файла и прогресса – переиндексированы: row 6 -> row 7
tk.Label(root, text="Текущий файла:", bg="#1e1e1e", fg="#d4d4d4").grid(row=7, column=0, columnspan=3, padx=5, pady=(5,0), sticky="w")
file_progress_bar = ttk.Progressbar(root, orient="horizontal", length=370, mode="determinate")
file_progress_bar.grid(row=7, column=1, columnspan=2, padx=5, pady=5, sticky="w")
file_progress_numeric_label = tk.Label(root, text="0%", bg="#1e1e1e", fg="#d4d4d4")
file_progress_numeric_label.grid(row=7, column=3, padx=5, pady=5, sticky="w")

# Метрки общего прогресса – переиндексированы: row 7 -> row 8
tk.Label(root, text="Общий прогресс:", bg="#1e1e1e", fg="#d4d4d4").grid(row=8, column=0, columnspan=3, padx=5, pady=(5,0), sticky="w")
overall_progress_bar = ttk.Progressbar(root, orient="horizontal", length=370, mode="determinate")
overall_progress_bar.grid(row=8, column=1, columnspan=2, padx=5, pady=5, sticky="w")
overall_progress_numeric_label = tk.Label(root, text="0%", bg="#1e1e1e", fg="#d4d4d4")
overall_progress_numeric_label.grid(row=8, column=3, padx=5, pady=5, sticky="w")

# Метки статуса и таймера – переиндексированы: row 8 -> row 9
status_label = tk.Label(root, text="Ожидание запуска конвертации", anchor="w", width=40, bg="#1e1e1e", fg="#d4d4d4")
status_label.grid(row=9, column=0, columnspan=2, padx=5, pady=5, sticky="we")
timer_label = tk.Label(root, text="Время: 0.0 сек", anchor="w", bg="#1e1e1e", fg="#d4d4d4")
timer_label.grid(row=9, column=2, padx=5, pady=5, sticky="w")

root.grid_columnconfigure(0, minsize=50)  # Настройка минимального размера первой колонки сетки


root.mainloop()  # Запуск главного цикла обработки событий графического интерфейса, что обеспечивает работоспособность приложения