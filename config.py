"""
Конфигурация для Nerpa GUI
Содержит константы, настройки и параметры по умолчанию
"""

from dataclasses import dataclass
from typing import Dict, List
from pathlib import Path

# Поддерживаемые форматы файлов
GENOME_FORMATS = ['.fasta', '.fa', '.fna', '.gbk', '.gb', '.json', '.predictions', '.txt']
SMILES_FORMAT = ['.tsv', '.txt']

# Расширения для отображения в file_uploader
GENOME_UPLOAD_TYPES = ['fasta', 'fa', 'fna', 'gbk', 'gb', 'json', '.predictions', '.txt']
SMILES_UPLOAD_TYPES = ['tsv', 'txt']

# Лимиты
MAX_FILE_SIZE_MB = 500
MAX_UPLOAD_FILES = 50
DEFAULT_TIMEOUT_SECONDS = 3600  # 1 час

# Пути
TEMP_DIR_PREFIX = "nerpa_gui_"
INPUT_SUBDIR = "input"
OUTPUT_SUBDIR = "output"

@dataclass
class NerpaParameters:
    """Параметры для запуска Nerpa (только реальные параметры Nerpa!)"""
    process_hybrids: bool = True
    threads: int = 4

# Параметры Nerpa с описаниями
NERPA_PARAMS_DESCRIPTIONS: Dict[str, str] = {
    'process_hybrids': 'Обрабатывать гибридные NRP-поликетидные кластеры',
    'process_class2': 'Обрабатывать кластеры класса II',
    'threads': 'Количество потоков для параллельного выполнения',
    'match_threshold': 'Минимальный порог совпадения (0.0-1.0)',
    'min_score': 'Минимальный score для отображения результатов',
    'max_results': 'Максимальное количество результатов'
}

# Описания форматов для пользователя
FORMAT_DESCRIPTIONS: Dict[str, str] = {
    'genome': """
**Геномные файлы:**
- FASTA (.fasta, .fa, .fna) - нуклеотидные последовательности
- GenBank (.gbk, .gb) - аннотированные последовательности
- antiSMASH JSON (.json) - результаты antiSMASH анализа
""",
    'smiles': """
**SMILES файл (TSV):**
- Табулированный файл с колонками: ID и SMILES структура
- Пример: compound1\\tCC(C)C(=O)N...
"""
}

# Настройки Streamlit
PAGE_CONFIG = {
    'page_title': 'Nerpa GUI - Анализ биосинтетических генных кластеров',
    'page_icon': '🧬',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded'
}

# Цветовая схема для графиков
PLOT_COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'warning': '#d62728',
    'info': '#9467bd',
    'gradient': ['#e3f2fd', '#2196f3', '#0d47a1']
}

# Валидационные правила
VALIDATION_RULES = {
    'min_file_size': 100,  # байт
    'max_file_size': MAX_FILE_SIZE_MB * 1024 * 1024,  # в байтах
    'min_smiles_columns': 2,
    'required_nerpa_version': '1.0'
}

# Сообщения об ошибках
ERROR_MESSAGES = {
    'file_too_large': f'Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE_MB} МБ',
    'invalid_format': 'Неподдерживаемый формат файла',
    'empty_file': 'Файл пустой или поврежден',
    'nerpa_not_found': 'Nerpa не найдена. Убедитесь, что она установлена и доступна в PATH',
    'execution_failed': 'Ошибка выполнения Nerpa. Проверьте входные данные',
    'timeout': 'Превышено время ожидания выполнения анализа',
    'no_results': 'Результаты не найдены. Возможно, не было найдено совпадений'
}

# Информация о приложении
APP_INFO = {
    'version': '1.0.0',
    'description': 'Графический интерфейс для Nerpa - инструмента связывания BGC и NRP структур',
    'github': 'https://github.com/ablab/nerpa',
    'citation': 'Nerpa: a tool for discovering biosynthetic gene clusters of bacterial nonribosomal peptides'
}
