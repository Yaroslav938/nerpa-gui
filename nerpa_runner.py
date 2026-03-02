"""
Обертка для запуска Nerpa (поддержка WSL + Windows + Linux)
"""

import subprocess
import re
import shutil
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from config import NerpaParameters, DEFAULT_TIMEOUT_SECONDS, ERROR_MESSAGES
from utils import logger, Timer


@dataclass
class NerpaResult:
    """Результат выполнения Nerpa"""
    success: bool
    output_dir: Optional[Path]
    execution_time: float
    stdout: str
    stderr: str
    error_message: Optional[str] = None
    log_path: Optional[Path] = None


def get_platform_info() -> Tuple[str, bool]:
    """Определение платформы"""
    system = platform.system()
    if system == "Linux":
        return "linux", False
    elif system == "Windows":
        return "windows", True
    elif system == "Darwin":
        return "macos", False
    else:
        return "unknown", False


def find_nerpa_executable() -> Optional[str]:
    """Поиск исполняемого файла nerpa.py"""
    system, use_wsl = get_platform_info()
    logger.info(f"[find_nerpa] Платформа: {system}")

    if system == "linux" or system == "macos":
        try:
            result = subprocess.run(
                ['which', 'nerpa.py'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip()
                logger.info(f"✅ Nerpa найдена: {path}")
                return path
        except Exception as e:
            logger.debug(f"which nerpa.py: {e}")

        try:
            result = subprocess.run(
                ['conda', 'run', '-n', 'nerpa_wsl', 'nerpa.py', '--help'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info("✅ Nerpa найдена через conda run")
                return 'linux-conda-run'
        except Exception as e:
            logger.debug(f"conda run: {e}")

        nerpa_path = shutil.which('nerpa.py')
        if nerpa_path:
            logger.info(f"✅ Nerpa найдена в PATH: {nerpa_path}")
            return nerpa_path

    elif system == "windows":
        logger.info("[find_nerpa] Windows: пробуем WSL...")

        # Вариант 1: conda run через WSL
        try:
            logger.info("[find_nerpa] Проверка: wsl conda run...")
            result = subprocess.run(
                ['wsl', '/home/yaroslav/miniconda3/bin/conda',
                 'run', '-n', 'nerpa_wsl', 'nerpa.py', '--help'],
                capture_output=True, text=True, timeout=30
            )
            logger.info(f"[find_nerpa] conda run returncode={result.returncode}")
            if result.returncode == 0:
                logger.info("✅ Nerpa найдена в WSL через conda run")
                return 'wsl-conda-run'
            else:
                logger.warning(f"[find_nerpa] conda run stderr: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"[find_nerpa] WSL conda run ошибка: {e}")

        # Вариант 2: прямой путь к nerpa.py в окружении
        try:
            logger.info("[find_nerpa] Проверка: прямой путь к nerpa.py...")
            result = subprocess.run(
                ['wsl', '/home/yaroslav/miniconda3/envs/nerpa_wsl/bin/nerpa.py', '--help'],
                capture_output=True, text=True, timeout=30
            )
            logger.info(f"[find_nerpa] direct path returncode={result.returncode}")
            if result.returncode == 0:
                logger.info("✅ Nerpa найдена в WSL через прямой путь")
                return 'wsl-direct-path'
            else:
                logger.warning(f"[find_nerpa] direct path stderr: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"[find_nerpa] WSL прямой путь ошибка: {e}")

        # Вариант 3: через bash -c с активацией conda
        try:
            logger.info("[find_nerpa] Проверка: wsl bash -c conda activate...")
            result = subprocess.run(
                ['wsl', 'bash', '-c',
                 'source /home/yaroslav/miniconda3/etc/profile.d/conda.sh && '
                 'conda activate nerpa_wsl && nerpa.py --help'],
                capture_output=True, text=True, timeout=30
            )
            logger.info(f"[find_nerpa] bash -c returncode={result.returncode}")
            if result.returncode == 0:
                logger.info("✅ Nerpa найдена через wsl bash -c")
                return 'wsl-bash-conda'
            else:
                logger.warning(f"[find_nerpa] bash -c stderr: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"[find_nerpa] wsl bash -c ошибка: {e}")

        # Вариант 4: нативный PATH Windows
        nerpa_path = shutil.which('nerpa.py')
        if nerpa_path:
            logger.info(f"✅ Nerpa найдена в Windows PATH: {nerpa_path}")
            return nerpa_path

    logger.warning("⚠️ Nerpa не найдена ни одним из способов")
    return None


def convert_to_wsl_path(windows_path: Path) -> str:
    """Конвертация Windows пути в WSL путь"""
    path_str = str(windows_path).replace('\\', '/')
    if ':' in path_str:
        drive, rest = path_str.split(':', 1)
        path_str = f"/mnt/{drive.lower()}{rest}"
    return path_str


class NerpaRunner:
    """Класс для запуска и управления Nerpa"""

    def __init__(self, input_dir: Path, output_dir: Path, params: NerpaParameters):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.params = params
        self.log_path = output_dir / "nerpa.log"
        self.nerpa_executable = find_nerpa_executable()
        self.system, self.use_wsl = get_platform_info()
        if not self.nerpa_executable:
            logger.error("❌ Nerpa не найдена при инициализации NerpaRunner!")
        else:
            logger.info(f"✅ NerpaRunner инициализирован: exe={self.nerpa_executable}")

    def build_command(
        self,
        smiles_file: Optional[Path] = None,
        predictions_list_file: Optional[Path] = None
    ) -> List[str]:
        """Формирование команды для запуска Nerpa"""
        if not self.nerpa_executable:
            raise FileNotFoundError(
                "Nerpa не найдена. Проверьте что WSL запущен и "
                "nerpa_wsl окружение активно."
            )

        exe = self.nerpa_executable
        is_wsl = exe in ('wsl-conda-run', 'wsl-direct-path', 'wsl-bash-conda')
        is_linux_conda = exe == 'linux-conda-run'

        if is_wsl:
            output_path = convert_to_wsl_path(self.output_dir)

            if predictions_list_file:
                predictions_wsl = convert_to_wsl_path(predictions_list_file)
                if exe == 'wsl-conda-run':
                    cmd = [
                        'wsl',
                        '/home/yaroslav/miniconda3/bin/conda', 'run',
                        '-n', 'nerpa_wsl',
                        'nerpa.py', '--predictions', predictions_wsl, '-o', output_path
                    ]
                elif exe == 'wsl-bash-conda':
                    cmd = [
                        'wsl', 'bash', '-c',
                        f'source /home/yaroslav/miniconda3/etc/profile.d/conda.sh && '
                        f'conda activate nerpa_wsl && '
                        f'nerpa.py --predictions {predictions_wsl} -o {output_path}'
                    ]
                else:
                    cmd = [
                        'wsl',
                        '/home/yaroslav/miniconda3/envs/nerpa_wsl/bin/nerpa.py',
                        '--predictions', predictions_wsl, '-o', output_path
                    ]
            else:
                input_path = convert_to_wsl_path(self.input_dir)
                if exe == 'wsl-conda-run':
                    cmd = [
                        'wsl',
                        '/home/yaroslav/miniconda3/bin/conda', 'run',
                        '-n', 'nerpa_wsl',
                        'nerpa.py', '-a', input_path, '-o', output_path
                    ]
                elif exe == 'wsl-bash-conda':
                    cmd = [
                        'wsl', 'bash', '-c',
                        f'source /home/yaroslav/miniconda3/etc/profile.d/conda.sh && '
                        f'conda activate nerpa_wsl && '
                        f'nerpa.py -a {input_path} -o {output_path}'
                    ]
                else:
                    cmd = [
                        'wsl',
                        '/home/yaroslav/miniconda3/envs/nerpa_wsl/bin/nerpa.py',
                        '-a', input_path, '-o', output_path
                    ]

            if smiles_file:
                smiles_path = convert_to_wsl_path(smiles_file)
                if exe == 'wsl-bash-conda':
                    # Для bash -c команда уже собрана как строка, дополняем её
                    cmd[-1] += f' --smiles-tsv {smiles_path}'
                else:
                    cmd.extend(['--smiles-tsv', smiles_path])

        elif is_linux_conda:
            if predictions_list_file:
                cmd = [
                    'conda', 'run', '-n', 'nerpa_wsl',
                    'nerpa.py', '--predictions', str(predictions_list_file),
                    '-o', str(self.output_dir)
                ]
            else:
                cmd = [
                    'conda', 'run', '-n', 'nerpa_wsl',
                    'nerpa.py', '-a', str(self.input_dir),
                    '-o', str(self.output_dir)
                ]
            if smiles_file:
                cmd.extend(['--smiles-tsv', str(smiles_file)])

        else:
            if exe.endswith('.py'):
                cmd = ['python', exe]
            else:
                cmd = [exe]
            if predictions_list_file:
                cmd.extend(['--predictions', str(predictions_list_file),
                             '-o', str(self.output_dir)])
            else:
                cmd.extend(['-a', str(self.input_dir), '-o', str(self.output_dir)])
            if smiles_file:
                cmd.extend(['--smiles-tsv', str(smiles_file)])

        # Общие параметры (не для bash -c строки)
        extra = []
        if hasattr(self.params, 'process_hybrids') and self.params.process_hybrids:
            extra.append('--process-hybrids')
        threads = getattr(self.params, 'threads', 4)
        if threads and threads > 0:
            extra.extend(['--threads', str(threads)])
        extra.append('--force-existing-outdir')

        if exe == 'wsl-bash-conda':
            cmd[-1] += ' ' + ' '.join(extra)
        else:
            cmd.extend(extra)

        logger.info(f"Команда Nerpa: {' '.join(cmd)}")
        return cmd

    def run(
        self,
        smiles_file: Optional[Path] = None,
        predictions_list_file: Optional[Path] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS
    ) -> NerpaResult:
        """Запуск Nerpa"""
        try:
            cmd = self.build_command(smiles_file, predictions_list_file)
            with Timer("Выполнение Nerpa") as timer:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(self.output_dir.parent)
                )
            logger.info(f"Nerpa stdout: {result.stdout[:500]}")
            if result.stderr:
                logger.warning(f"Nerpa stderr: {result.stderr[:500]}")

            if result.returncode == 0:
                return NerpaResult(
                    success=True,
                    output_dir=self.output_dir,
                    execution_time=timer.elapsed,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    log_path=self.log_path if self.log_path.exists() else None
                )
            else:
                return NerpaResult(
                    success=False,
                    output_dir=self.output_dir,
                    execution_time=timer.elapsed,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    error_message=f"Код ошибки {result.returncode}: {result.stderr[:500]}"
                )

        except subprocess.TimeoutExpired:
            return NerpaResult(
                success=False,
                output_dir=None,
                execution_time=timeout,
                stdout="",
                stderr="",
                error_message=ERROR_MESSAGES['timeout']
            )
        except Exception as e:
            return NerpaResult(
                success=False,
                output_dir=None,
                execution_time=0,
                stdout="",
                stderr="",
                error_message=f"Ошибка: {str(e)}"
            )

    def parse_log(self) -> Dict[str, any]:
        """Парсинг лог-файла Nerpa"""
        if not self.log_path or not self.log_path.exists():
            return {}
        info = {'total_bgcs': 0, 'matches_found': 0, 'errors': [], 'warnings': []}
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            bgc_match = re.search(r'Found (\d+) BGCs?', content, re.IGNORECASE)
            if bgc_match:
                info['total_bgcs'] = int(bgc_match.group(1))
            matches_match = re.search(r'Found (\d+) matches?', content, re.IGNORECASE)
            if matches_match:
                info['matches_found'] = int(matches_match.group(1))
        except:
            pass
        return info

    def check_output_files(self) -> Tuple[bool, List[str]]:
        """Проверка наличия выходных файлов"""
        expected_files = ['report.csv']
        found_files = []
        for filename in expected_files:
            file_path = self.output_dir / filename
            if file_path.exists():
                found_files.append(filename)
        details_dir = self.output_dir / 'details'
        if details_dir.exists() and details_dir.is_dir():
            detail_files = list(details_dir.glob('*.txt'))
            if detail_files:
                found_files.append(f'details/ ({len(detail_files)} files)')
        all_present = len(found_files) >= len(expected_files)
        return all_present, found_files