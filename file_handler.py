"""
Обработка загрузки и валидации файлов
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import tempfile
import streamlit as st

from config import (
    GENOME_FORMATS, SMILES_FORMAT, VALIDATION_RULES,
    ERROR_MESSAGES, TEMP_DIR_PREFIX, INPUT_SUBDIR, OUTPUT_SUBDIR
)
from utils import logger, sanitize_filename, format_file_size


class FileHandler:
    """Класс для работы с файлами"""
    
    def __init__(self):
        self.temp_dir: Optional[Path] = None
        self.input_dir: Optional[Path] = None
        self.antismash_dir: Optional[Path] = None
        self.output_dir: Optional[Path] = None
    
    def create_temp_structure(self) -> Tuple[Path, Path, Path, Path]:
        """Создание структуры временных директорий"""
        try:
            self.temp_dir = Path(tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX))
            self.input_dir = self.temp_dir / INPUT_SUBDIR
            self.antismash_dir = self.temp_dir / "antismash_out"
            self.output_dir = self.temp_dir / OUTPUT_SUBDIR
            
            self.input_dir.mkdir(exist_ok=True)
            self.antismash_dir.mkdir(exist_ok=True)
            self.output_dir.mkdir(exist_ok=True)
            
            logger.info(f"Создана временная структура: {self.temp_dir}")
            return self.temp_dir, self.input_dir, self.antismash_dir, self.output_dir
            
        except Exception as e:
            logger.error(f"Ошибка создания временных директорий: {e}")
            raise
    
    def cleanup(self) -> None:
        """Очистка временных файлов и директорий"""
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Временная директория удалена: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временную директорию: {e}")

def validate_genome_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Улучшенная валидация геномного файла"""
    try:
        if file_path.suffix.lower() not in GENOME_FORMATS:
            return False, f"Неподдерживаемый формат: {file_path.suffix}"
        
        file_size = file_path.stat().st_size
        if file_size < VALIDATION_RULES['min_file_size']:
            return False, ERROR_MESSAGES['empty_file']
        if file_size > VALIDATION_RULES['max_file_size']:
            return False, ERROR_MESSAGES['file_too_large']
        
        # Читаем первые 4000 символов, чтобы игнорировать пустые строки в начале
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(4000).strip()
            
            if file_path.suffix.lower() in ['.fasta', '.fa', '.fna']:
                if not content.startswith('>'):
                    return False, "FASTA файл должен начинаться с '>'"
            elif file_path.suffix.lower() in ['.gbk', '.gb']:
                if 'LOCUS' not in content:
                    return False, "GenBank файл должен содержать 'LOCUS'"
            elif file_path.suffix.lower() == '.json':
                if not (content.startswith('{') or content.startswith('[')):
                    return False, "JSON файл должен начинаться с '{' или '['"
            elif file_path.suffix.lower() in ['.predictions', '.txt']:
                if not content or len(content) < 5:
                    return False, "Файл пустой или поврежден"
        
        return True, None
    except Exception as e:
        return False, f"Ошибка валидации: {str(e)}"

def validate_smiles_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Валидация SMILES TSV файла"""
    try:
        if file_path.suffix.lower() not in SMILES_FORMAT:
            return False, f"Неподдерживаемый формат: {file_path.suffix}"
        
        file_size = file_path.stat().st_size
        if file_size < VALIDATION_RULES['min_file_size']:
            return False, ERROR_MESSAGES['empty_file']
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 5: break
                parts = line.strip().split('\t')
                if len(parts) < VALIDATION_RULES['min_smiles_columns']:
                    return False, f"Строка {i+1}: недостаточно колонок"
        return True, None
    except Exception as e:
        return False, f"Ошибка валидации: {str(e)}"

def save_uploaded_file(uploaded_file, target_dir: Path) -> Tuple[Optional[Path], Optional[str]]:
    try:
        safe_name = sanitize_filename(uploaded_file.name)
        file_path = target_dir / safe_name
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        return file_path, None
    except Exception as e:
        return None, str(e)

def save_uploaded_files(uploaded_files: List, target_dir: Path, file_type: str = 'genome') -> List[Path]:
    valid_files = []
    for uploaded_file in uploaded_files:
        file_path, error = save_uploaded_file(uploaded_file, target_dir)
        if error: continue
        is_valid, error_msg = validate_genome_file(file_path) if file_type == 'genome' else validate_smiles_file(file_path)
        
        if is_valid:
            valid_files.append(file_path)
        else:
            try: file_path.unlink()
            except: pass
    return valid_files