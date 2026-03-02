"""
Вспомогательные функции для Nerpa GUI
"""

import uuid
import time
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, Any
from functools import wraps
import streamlit as st

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} ТБ"


def format_execution_time(seconds: float) -> str:
    """
    Форматирование времени выполнения
    
    Args:
        seconds: Время в секундах
        
    Returns:
        Строка с временем (например, "2 мин 30 сек")
    """
    if seconds is None:
        return "N/A"
    
    try:
        seconds = float(seconds)
    except (ValueError, TypeError):
        return "N/A"
    
    if seconds < 60:
        return f"{seconds:.1f} сек"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} мин {secs} сек"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} ч {minutes} мин"


def generate_session_id() -> str:
    """Генерация уникального ID для сессии"""
    return str(uuid.uuid4())


def sanitize_filename(filename: str) -> str:
    """Очистка имени файла от недопустимых символов"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    if len(name) > 200:
        name = name[:200]
    
    return f"{name}.{ext}" if ext else name


def validate_nerpa_installation() -> Tuple[bool, Optional[str]]:
    """
    Проверка установки Nerpa (проверяет WSL с прямыми путями)
    
    Returns:
        Tuple: (установлена ли Nerpa, сообщение)
    """
    # Вариант 1: conda run
    try:
        result = subprocess.run(
            ['wsl', '/home/yaroslav/miniconda3/bin/conda', 'run', '-n', 'nerpa_wsl', 'nerpa.py', '--help'],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            logger.info("✅ Nerpa найдена в WSL через conda run")
            return True, "Найдена в WSL (conda run)"
    except Exception as e:
        logger.debug(f"conda run проверка: {e}")
    
    # Вариант 2: Прямой путь
    try:
        result = subprocess.run(
            ['wsl', '/home/yaroslav/miniconda3/envs/nerpa_wsl/bin/nerpa.py', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            logger.info("✅ Nerpa найдена в WSL через прямой путь")
            return True, "Найдена в WSL (прямой путь)"
    except Exception as e:
        logger.debug(f"Прямой путь проверка: {e}")
    
    # Вариант 3: Windows PATH
    import shutil
    if shutil.which('nerpa.py') or shutil.which('nerpa'):
        return True, "Найдена в Windows"
    
    return False, "Nerpa не найдена. Проверьте пути к WSL."




def get_nerpa_version() -> Optional[str]:
    """Получение версии Nerpa"""
    # Пробуем WSL
    try:
        result = subprocess.run(
            ['wsl', 'nerpa.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "WSL version"
    except:
        pass
    
    # Пробуем Windows
    try:
        result = subprocess.run(
            ['nerpa.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "Windows version"
    except:
        pass
    
    return None


def error_handler(func):
    """Декоратор для обработки ошибок"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {str(e)}", exc_info=True)
            st.error(f"Произошла ошибка: {str(e)}")
            return None
    return wrapper


def create_download_button(data: Any, filename: str, label: str, mime_type: str = "text/csv") -> None:
    """Создание кнопки скачивания"""
    st.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime=mime_type
    )


class Timer:
    """Контекстный менеджер для измерения времени"""
    
    def __init__(self, name: str = "Операция"):
        self.name = name
        self.start_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"{self.name} начата")
        return self
    
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        logger.info(f"{self.name} завершена за {format_execution_time(self.elapsed)}")


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Безопасное деление"""
    try:
        return numerator / denominator if denominator != 0 else default
    except:
        return default
