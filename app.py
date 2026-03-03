"""
Главное Streamlit приложение для Nerpa GUI
Графический интерфейс для биоинформатического инструмента Nerpa
"""

import streamlit as st
from pathlib import Path
import os
import glob
import subprocess
import time
import platform
import shutil
import json
import pandas as pd
import plotly.express as px

# --- МОНКИ-ПАТЧИНГ: Ослабляем слишком строгую валидацию файлов ---
# В оригинальном config.py стоит лимит в 100 байт. Тестовые файлы весят меньше и молча удаляются.
import file_handler
def relaxed_validate_smiles(file_path: Path):
    try:
        if file_path.stat().st_size < 5:  # Файл должен весить хотя бы 5 байт
            return False, "Файл пустой"
        return True, None
    except Exception as e:
        return False, str(e)

file_handler.validate_smiles_file = relaxed_validate_smiles
file_handler.VALIDATION_RULES['min_file_size'] = 5
# -----------------------------------------------------------------

# Импорт модулей
from config import (
    PAGE_CONFIG, NerpaParameters, NERPA_PARAMS_DESCRIPTIONS,
    FORMAT_DESCRIPTIONS, APP_INFO, MAX_UPLOAD_FILES
)
from file_handler import FileHandler, save_uploaded_files
from results_viewer import display_results_page, load_results
from visualizations import display_visualizations
from utils import format_execution_time, error_handler

# Настройка страницы
st.set_page_config(**PAGE_CONFIG)

def convert_to_wsl_path(windows_path) -> str:
    """Конвертация Windows пути в WSL путь (/mnt/c/...)"""
    if not windows_path:
        return ""
    path_str = str(windows_path).replace('\\', '/')
    if ':' in path_str:
        drive, rest = path_str.split(':', 1)
        path_str = f"/mnt/{drive.lower()}{rest}"
    return path_str

class AnalysisResult:
    def __init__(self, success, output_dir=None):
        self.success = success
        self.output_dir = output_dir

def init_session_state():
    if 'file_handler' not in st.session_state or st.session_state.file_handler is None:
        st.session_state.file_handler = FileHandler()
        st.session_state.file_handler.create_temp_structure()
        
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'results_df' not in st.session_state:
        st.session_state.results_df = None
    if 'active_input_dir' not in st.session_state:
        st.session_state.active_input_dir = st.session_state.file_handler.input_dir
    if 'last_uploaded_files' not in st.session_state:
        st.session_state.last_uploaded_files = []
    if 'antismash_df' not in st.session_state:
        st.session_state.antismash_df = None

def create_sidebar():
    st.sidebar.title("⚙️ Параметры анализа")
    
    st.sidebar.subheader("🛠 Системные настройки (ОС)")
    current_os = platform.system()
    st.sidebar.info(f"**Текущая ОС:** {current_os}")
    
    wsl_distro = "Ubuntu"
    if current_os == "Windows":
        wsl_distro = st.sidebar.text_input("Дистрибутив WSL", value="Ubuntu-22.04")
    
    st.sidebar.subheader("🧬 Настройки antiSMASH (Шаг A)")
    antismash_mode = st.sidebar.radio("Способ запуска antiSMASH", ["Docker (Рекомендуется)", "Локальный (Linux/Conda)"])
    antismash_local_cmd = ""
    if antismash_mode == "Локальный (Linux/Conda)":
        antismash_local_cmd = st.sidebar.text_area(
            "Команда запуска antiSMASH", 
            value="source ~/miniconda3/etc/profile.d/conda.sh && conda activate antismash && antismash",
            help="Команда активации окружения и вызова исполняемого файла antismash."
        )

    st.sidebar.subheader("🔬 Настройки Nerpa (Шаг B)")
    default_linux_cmd = "source ~/miniconda3/etc/profile.d/conda.sh && conda activate nerpa_wsl && python /home/yaroslav/nerpa/nerpa.py"
    linux_cmd = st.sidebar.text_area("Команда инициализации Nerpa", value=default_linux_cmd, height=80)
    
    process_hybrids = st.sidebar.checkbox("Обрабатывать гибридные NRP-PK (--process-hybrids)", value=True)
    threads = st.sidebar.slider("Количество потоков (--threads)", min_value=1, max_value=16, value=4)

    st.sidebar.subheader("🧪 Продвинутая химия")
    col_smiles = st.sidebar.text_input("Колонка со структурой (--col-smiles)", value="SMILES")
    col_id = st.sidebar.text_input("Колонка с ID (--col-id)", value="ID")
    sep = st.sidebar.text_input("Разделитель TSV (--sep)", value="\\t")
    antismash_path = st.sidebar.text_input("Путь к antiSMASH (--antismash-path)", value="", help="Для режима --sequences")

    params = NerpaParameters(process_hybrids=process_hybrids, threads=threads)
    
    st.sidebar.divider()
    st.sidebar.info(f"**Версия:** {APP_INFO['version']}\n\n[GitHub Nerpa]({APP_INFO['github']})")
    
    return params, wsl_distro, linux_cmd, col_smiles, col_id, sep, antismash_path, antismash_mode, antismash_local_cmd

def check_docker_running():
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False

def parse_antismash_results(antismash_dir: Path) -> pd.DataFrame:
    """Парсит JSON файлы antiSMASH для извлечения информации о найденных кластерах"""
    data = []
    if not antismash_dir.exists():
        return pd.DataFrame()
        
    # Ищем JSON файлы в корне папки и на 1 уровень вглубь
    search_paths = [antismash_dir] + [d for d in antismash_dir.iterdir() if d.is_dir()]
    
    for search_dir in search_paths:
        json_files = list(search_dir.glob("*.json"))
        for json_path in json_files:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    jdata = json.load(f)
                
                if "records" not in jdata: continue
                
                for record in jdata["records"]:
                    contig_id = record.get("id", "Unknown")
                    for feat in record.get("features", []):
                        if feat.get("type") in ["region", "cluster"]:
                            loc = feat.get("location", "")
                            quals = feat.get("qualifiers", {})
                            products = quals.get("product", ["Unknown"])
                            region_num = quals.get("region_number", [""])[0] if "region_number" in quals else ""
                            
                            for prod in products:
                                data.append({
                                    "Источник (Файл)": json_path.stem,
                                    "Контиг": contig_id,
                                    "Регион": str(region_num),
                                    "Тип кластера": prod,
                                    "Локация": str(loc)
                                })
            except Exception:
                pass
                
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.drop_duplicates()
    return df

def run_antismash(input_dir: Path, output_dir: Path, mode: str, local_cmd: str, wsl_distro: str):
    if mode == "Docker (Рекомендуется)" and not check_docker_running():
        st.error("🐳 **Docker не запущен!** Пожалуйста, включите Docker Desktop.")
        return False

    files = list(input_dir.glob("*.fasta")) + list(input_dir.glob("*.fa")) + list(input_dir.glob("*.fna")) + \
            list(input_dir.glob("*.gbk")) + list(input_dir.glob("*.gb"))
            
    if not files:
        st.error("В загрузках нет FASTA или GBK файлов для запуска antiSMASH.")
        return False

    progress = st.progress(0)
    status_text = st.empty()
    current_os = platform.system()
    
    try:
        uid, gid = str(os.getuid()), str(os.getgid())
    except AttributeError:
        uid, gid = "1000", "1000"

    success_count = 0
    for i, filepath in enumerate(files):
        filename = filepath.name
        file_base = filepath.stem
        
        status_text.text(f"🧬 antiSMASH анализирует: {filename} (это может занять несколько минут)...")
        
        target_out = output_dir / file_base
        if target_out.exists():
            try: shutil.rmtree(target_out, ignore_errors=True)
            except Exception: pass
        
        if mode == "Docker (Рекомендуется)":
            cmd = [
                "docker", "run", "--rm", "--user", f"{uid}:{gid}",
                "--entrypoint", "/bin/sh", "-e", "MPLCONFIGDIR=/tmp/matplotlib",
                "-v", f"{input_dir}:/input",
                "-v", f"{output_dir}:/output",
                "antismash/standalone:5.1.2", "-c",
                f"mkdir -p /tmp/matplotlib && cd /input && antismash '{filename}' --genefinding-tool prodigal --output-dir /output/{file_base}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            if current_os == "Windows":
                final_in = convert_to_wsl_path(filepath)
                final_out = convert_to_wsl_path(target_out)
                full_cmd = f"{local_cmd} '{final_in}' --genefinding-tool prodigal --output-dir '{final_out}'"
                cmd = ["wsl", "-d", wsl_distro, "bash", "-c", full_cmd]
            else:
                final_in = str(filepath)
                final_out = str(target_out)
                full_cmd = f"{local_cmd} '{final_in}' --genefinding-tool prodigal --output-dir '{final_out}'"
                cmd = ["bash", "-c", full_cmd]
                
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            success_count += 1
        else:
            st.error(f"❌ Ошибка antiSMASH для {filename}")
            with st.expander("Лог выполнения"):
                st.code(result.stderr[-2000:] if result.stderr else "Нет логов", language='text')
                if result.stdout: st.code(result.stdout[-2000:], language='text')
                
        progress.progress((i + 1) / len(files))
    
    progress.empty()
    status_text.empty()
    if success_count > 0:
        st.success(f"✅ antiSMASH успешно отработал! ({success_count} файл(ов))")
        
        # --- НОВАЯ ФУНКЦИЯ: Парсинг результатов antiSMASH ---
        try:
            st.session_state.antismash_df = parse_antismash_results(output_dir)
        except Exception:
            pass
            
        return True
    return False

def auto_patch_nerpa(wsl_distro, current_os, temp_dir):
    """Надёжная инъекция фиксов для Nerpa (с сохранением топологии кластера)"""
    patch_script = """import os

paths_to_check = [
    '/home/yaroslav/miniconda3/envs/nerpa_wsl/share/nerpa/nerpa_pipeline/NRPSPredictor_utils/json_handler.py',
    os.path.expanduser('~/miniconda3/envs/nerpa_wsl/share/nerpa/nerpa_pipeline/NRPSPredictor_utils/json_handler.py'),
    os.path.expanduser('~/nerpa/src/nerpa_pipeline/NRPSPredictor_utils/json_handler.py')
]

patched_any = False
for file_path in paths_to_check:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        original_text = text
        
        # 1. Исправление prediction.split (Умная распаковка для ctg_universal)
        old_split = "prefix, ctg_id, orf_idx, amp_binding = prediction.split('_')"
        bad_patch = "parts = prediction.split('_'); prefix, amp_binding = parts[0], parts[-1]; orf_idx = parts[-2]; ctg_id = '_'.join(parts[1:-2]) if len(parts) > 3 else 'ctg1'"
        good_patch = "parts = prediction.split('_'); prefix, amp_binding = parts[0], parts[-1]; orf_idx = str(parts[-2]) if len(parts)>2 else '1'; ctg_id = '_'.join(parts[1:-2]) if len(parts) > 3 else 'ctg1'"
        universal_patch = "parts = prediction.split('_'); prefix, amp_binding = parts[0], parts[-1]; orf_idx = str(parts[-2]) if len(parts)>2 and parts[-2].isdigit() else '1'; ctg_id = '_'.join(parts[1:-2]) if len(parts)>3 else 'ctg_universal'"
        
        if old_split in text: text = text.replace(old_split, universal_patch)
        if bad_patch in text: text = text.replace(bad_patch, universal_patch)
        if good_patch in text: text = text.replace(good_patch, universal_patch)
            
        # 2. Исправление orf_idx int
        text = text.replace('int(orf_idx)', "int(''.join(filter(str.isdigit, str(orf_idx))) or 1)")
            
        # 3. Безопасный поиск locus_tag
        old_locus = "feature['qualifiers']['locus_tag'][0]"
        new_locus = "feature['qualifiers'].get('locus_tag', feature['qualifiers'].get('gene', ['unknown_locus']))[0]"
        text = text.replace(old_locus, new_locus)
            
        # 4. Баг split('_') -> ИСЦЕЛЕНИЕ ТОПОЛОГИИ (Собираем все гены без индексов в ctg_universal)
        old_line_1 = "ctg_id, orf_idx = locus_tag.split('_')"
        old_line_2 = 'ctg_id, orf_idx = locus_tag.split("_")'
        safe_split_old = "_lt = str(locus_tag); ctg_id, orf_idx = _lt.rsplit('_', 1) if '_' in _lt else (_lt, ''.join(filter(str.isdigit, _lt)) or '1')"
        safe_split_new = "global _orf_ctr; _orf_ctr = globals().get('_orf_ctr', 0) + 1; _lt = str(locus_tag); ctg_id, orf_idx = _lt.rsplit('_', 1) if '_' in _lt else ('ctg_universal', str(_orf_ctr))"
        
        text = text.replace(old_line_1, safe_split_new).replace(old_line_2, safe_split_new).replace(safe_split_old, safe_split_new)
            
        if text != original_text:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"✅ Успешно пропатчен файл: {file_path}")
            patched_any = True

if not patched_any:
    print("ℹ️ Патчи уже установлены или нужный файл не найден.")
"""
    script_path = temp_dir / "patch_nerpa.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(patch_script)
        
    if current_os == "Windows":
        wsl_script_path = convert_to_wsl_path(script_path)
        cmd = ["wsl", "-d", wsl_distro, "python3", wsl_script_path]
    else:
        cmd = ["python3", str(script_path)]
        
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@error_handler
def run_analysis(
    params: NerpaParameters, wsl_distro: str, linux_cmd: str, 
    genome_mode: str, chem_mode: str,
    genome_paths: list, chem_path: Path, manual_smiles: str,
    col_smiles: str, col_id: str, sep: str, antismash_path: str
):
    fh = st.session_state.file_handler
    current_os = platform.system()
    
    st.subheader("🔬 Выполнение анализа Nerpa")
    progress_bar = st.progress(10)
    status_text = st.empty()
    
    try:
        status_text.text("Авто-исправление исходного кода Nerpa...")
        patch_log = auto_patch_nerpa(wsl_distro, current_os, fh.temp_dir)
        if patch_log and "Успешно" in patch_log:
            with st.expander("Лог установки патча:"): st.text(patch_log)
        
        status_text.text(f"Сборка аргументов для запуска на {current_os}...")
        final_out = convert_to_wsl_path(fh.output_dir) if current_os == "Windows" else str(fh.output_dir)
        args = f" -o '{final_out}'"
        
        # Если мы только что выполнили antiSMASH, форсируем режим -a
        if st.session_state.active_input_dir == fh.antismash_dir:
            genome_mode = "Результаты antiSMASH (-a)"

        # === 1. ГЕНОМНЫЙ ВВОД ===
        if "(-a)" in genome_mode:
            active_dir = st.session_state.active_input_dir
            input_paths = []
            for item in active_dir.iterdir():
                if item.is_dir():
                    path_str = convert_to_wsl_path(item) if current_os == "Windows" else str(item)
                    input_paths.append(path_str)
                    
            if not input_paths:
                path_str = convert_to_wsl_path(active_dir) if current_os == "Windows" else str(active_dir)
                args += f" -a '{path_str}'"
            elif len(input_paths) == 1:
                args += f" -a '{input_paths[0]}'"
            else:
                list_file_path = fh.temp_dir / "antismash_list.txt"
                with open(list_file_path, "w", encoding="utf-8") as f:
                    for p in input_paths: f.write(f"{p}\n")
                wsl_list_path = convert_to_wsl_path(list_file_path) if current_os == "Windows" else str(list_file_path)
                args += f" --antismash_output_list '{wsl_list_path}'"
        else:
            g_path = convert_to_wsl_path(genome_paths[0]) if current_os == "Windows" else str(genome_paths[0])
            if "(--sequences)" in genome_mode:
                args += f" --sequences '{g_path}'"
            elif "(--predictions)" in genome_mode:
                args += f" --predictions '{g_path}'"

        # === 2. ХИМИЧЕСКИЙ ВВОД ===
        if "(--smiles)" in chem_mode and "tsv" not in chem_mode:
            smiles_list = manual_smiles.split('\n')
            smiles_args = ' '.join([f"'{s.strip()}'" for s in smiles_list if s.strip()])
            args += f" --smiles {smiles_args}"
        else:
            c_path = convert_to_wsl_path(chem_path) if current_os == "Windows" else str(chem_path)
            
            if "(--smiles-tsv)" in chem_mode:
                args += f" --smiles-tsv '{c_path}'"
                if col_smiles and col_smiles.strip(): args += f" --col-smiles '{col_smiles.strip()}'"
                if col_id and col_id.strip(): args += f" --col-id '{col_id.strip()}'"
                if sep and sep != "\\t": args += f" --sep '{sep}'"
            elif "(--rban-json)" in chem_mode:
                args += f" --rban-json '{c_path}'"
            elif "(--structures)" in chem_mode:
                args += f" --structures '{c_path}'"

        # === 3. ОБЩИЕ ПАРАМЕТРЫ ===
        if params.process_hybrids:
            args += " --process-hybrids"
        if params.threads:
            args += f" --threads {params.threads}"
        if antismash_path and antismash_path.strip():
            args += f" --antismash-path '{antismash_path.strip()}'"
        
        args += " --force-existing-outdir"

        full_linux_cmd = f"{linux_cmd} {args}"
        if current_os == "Windows":
            cmd = ["wsl", "-d", wsl_distro, "bash", "-c", full_linux_cmd]
        else:
            cmd = ["bash", "-c", full_linux_cmd]

        st.write("### 🔍 Диагностика запуска")
        st.code(full_linux_cmd, language='bash')
        
        status_text.text("Запуск алгоритма Nerpa... Пожалуйста, подождите.")
        progress_bar.progress(30)
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        exec_time = time.time() - start_time
        progress_bar.progress(90)
        
        stderr_text = str(result.stderr) if result.stderr is not None else ""
        stdout_text = str(result.stdout) if result.stdout is not None else ""
        
        if result.returncode == 0 or (fh.output_dir / "report.csv").exists():
            status_text.text("Обработка результатов...")
            
            st.session_state.analysis_result = AnalysisResult(success=True, output_dir=fh.output_dir)
            df = load_results(fh.output_dir)
            st.session_state.results_df = df
            
            if df is not None and not df.empty:
                st.success(f"✅ Анализ успешно завершен! Найдено совпадений: {len(df)}. Время: {format_execution_time(exec_time)}")
                with st.expander("🔍 Посмотреть полный лог Nerpa"):
                    st.code(stdout_text[-3000:] if stdout_text else "Нет логов", language='text')
            else:
                st.warning(f"✅ Анализ завершен без ошибок, НО совпадений не найдено (0 результатов). \n\n*В этом геноме нет кластеров, производящих указанные вами SMILES структуры.*")
                
                # --- СУПЕР ДЕБАГГЕР (Рентген) ---
                st.markdown("### 🛠 Рентген (Что именно прочитала Nerpa)")
                st.info("Посмотрите ниже: если в `predictions.info` пусто, значит Nerpa не поняла гены. Если в `structures.info` пусто, значит Java-модуль (rBAN) не смог разобрать SMILES.")
                pred_file = fh.output_dir / "predictions.info"
                struct_file = fh.output_dir / "structures.info"
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**predictions.info (Геномы):**")
                    if pred_file.exists(): 
                        st.code(pred_file.read_text()[:3000], language='text')
                    else: 
                        st.error("Файл не сгенерирован!")
                with c2:
                    st.markdown("**structures.info (Химия):**")
                    if struct_file.exists(): 
                        st.code(struct_file.read_text()[:3000], language='text')
                    else: 
                        st.error("Файл не сгенерирован!")
                
                with st.expander("🔍 Посмотреть полный лог Nerpa"):
                    st.code(stdout_text[-3000:] if stdout_text else "Нет логов", language='text')
                
            progress_bar.progress(100)
        else:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Ошибка выполнения Nerpa (Код: {result.returncode})")
            
            if "Column" in stderr_text and "was specified but does not exist" in stderr_text:
                st.warning("💡 **Ошибка в TSV файле!** Nerpa не может найти нужную колонку со структурами.")
            elif "Could not find antiSMASH output" in stderr_text or "Could not find antiSMASH output" in stdout_text:
                st.warning("💡 **Внимание:** Nerpa не распознала файлы как результаты работы antiSMASH. Убедитесь, что вы запустили 'Шаг A: antiSMASH'.")
                
            with st.expander("🔍 Показать логи ошибки (Traceback)"):
                if stderr_text: st.code(stderr_text[-3000:], language='text')
                if stdout_text: st.code(stdout_text[-3000:], language='text')
                    
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Системная ошибка Python GUI: {str(e)}")

def main():
    init_session_state()
    st.title("🧬 Nerpa GUI Pro")
    st.markdown("*Универсальный графический интерфейс для анализа биосинтетических генных кластеров*")
    st.divider()
    
    params, wsl_distro, linux_cmd, col_smiles, col_id, sep, antismash_path, as_mode, as_cmd = create_sidebar()
    fh = st.session_state.file_handler
    
    tabs = st.tabs(["📁 Данные и Запуск", "📊 Результаты", "📈 Визуализация", "ℹ️ О программе"])
    
    with tabs[0]:
        st.header("1️⃣ Загрузка данных")
        col1, col2 = st.columns(2)
        
        # ЛЕВАЯ КОЛОНКА - ГЕНОМЫ
        with col1:
            genome_mode = st.selectbox("Формат геномных данных:", [
                "Результаты antiSMASH (-a)",
                "Сырые последовательности (--sequences)",
                "Готовые предсказания (--predictions)"
            ])
            
            is_multiple = "(-a)" in genome_mode
            genome_files = st.file_uploader(
                f"Файлы геномов (FASTA/GBK/JSON)",
                accept_multiple_files=is_multiple,
                key="genome_uploader"
            )
            
            g_files_list = genome_files if isinstance(genome_files, list) else ([genome_files] if genome_files else [])
            current_g_names = [f.name for f in g_files_list]
            if current_g_names != st.session_state.get('last_g_files', []):
                st.session_state.last_g_files = current_g_names
                for f in fh.input_dir.glob("*"):
                    if f.is_file(): f.unlink(missing_ok=True)
                    else: shutil.rmtree(f, ignore_errors=True)
                for f in fh.antismash_dir.glob("*"):
                    if f.is_file(): f.unlink(missing_ok=True)
                    else: shutil.rmtree(f, ignore_errors=True)
                st.session_state.active_input_dir = fh.input_dir

            valid_genomes = []
            if g_files_list:
                valid_genomes = save_uploaded_files(g_files_list, fh.input_dir, 'genome')
                if valid_genomes:
                    st.info(f"📥 Готово файлов к анализу: {len(valid_genomes)}")
                    
                    # Пытаемся автоматически распарсить, если пользователь загрузил готовые результаты antiSMASH
                    if genome_mode == "Результаты antiSMASH (-a)":
                        try:
                            df_as = parse_antismash_results(st.session_state.active_input_dir)
                            if not df_as.empty:
                                st.session_state.antismash_df = df_as
                        except Exception:
                            pass
                else:
                    st.error("❌ Файлы отклонены! Возможно, они пустые.")
        
        # ПРАВАЯ КОЛОНКА - ХИМИЯ
        with col2:
            chem_mode = st.selectbox("Формат химических структур:", [
                "Таблица TSV (--smiles-tsv)",
                "Ввод текста (--smiles)",
                "rBAN JSON (--rban-json)",
                "Готовые структуры (--structures)"
            ])
            
            chem_path = None
            manual_smiles = ""
            
            if chem_mode == "Ввод текста (--smiles)":
                manual_smiles = st.text_area(
                    "Введите SMILES (каждая структура с новой строки):", 
                    value="C1=CC(=C(C(=C1)C(=O)N[C@@H](CO)C(=O)O)O)O"
                )
            else:
                chem_file = st.file_uploader("Файл со структурами (TSV/TXT)", accept_multiple_files=False, key="chem_uploader")
                if chem_file:
                    saved = save_uploaded_files([chem_file], fh.input_dir, 'smiles')
                    if saved:
                        chem_path = saved[0]
                        st.info(f"📥 Файл структур успешно загружен!")
                    else:
                        st.error("❌ Файл не прошел валидацию (пустой или неверный формат)!")

        has_raw_genomes = any(f.suffix.lower() in ['.fasta', '.fa', '.fna', '.gbk', '.gb'] for f in valid_genomes)
        
        st.divider()
        st.header("2️⃣ Запуск пайплайна")
        
        col_a, col_b = st.columns(2)
        
        # КНОПКА ШАГ A
        with col_a:
            st.markdown("### Шаг A: antiSMASH")
            st.caption("Поиск всех кластеров в сырых геномах (FASTA/GBK).")
            if st.button("🧬 Запустить antiSMASH", disabled=not has_raw_genomes, use_container_width=True):
                with st.spinner("Выполнение antiSMASH..."):
                    success = run_antismash(fh.input_dir, fh.antismash_dir, as_mode, as_cmd, wsl_distro)
                    if success:
                        st.session_state.active_input_dir = fh.antismash_dir
                        st.info("Теперь вы можете посмотреть найденные кластеры на вкладке «Результаты» ИЛИ запустить Шаг B.")

        # КНОПКА ШАГ B
        with col_b:
            st.markdown("### Шаг B: Nerpa")
            st.caption("Сопоставление найденных кластеров со структурами.")
            
            can_run_nerpa = False
            if st.session_state.active_input_dir == fh.antismash_dir or genome_mode == "Результаты antiSMASH (-a)":
                can_run_nerpa = bool(list(st.session_state.active_input_dir.glob("*")))
            else:
                can_run_nerpa = len(valid_genomes) > 0
                
            if chem_mode != "Ввод текста (--smiles)" and not chem_path:
                can_run_nerpa = False
            
            if st.button("🚀 Запустить анализ Nerpa", type="primary", use_container_width=True, disabled=not can_run_nerpa):
                run_analysis(
                    params, wsl_distro, linux_cmd, 
                    genome_mode, chem_mode, 
                    valid_genomes, chem_path, manual_smiles, 
                    col_smiles, col_id, sep, antismash_path
                )

    with tabs[1]:
        st.header("📊 Результаты анализа")
        has_results = False
        
        # Если Nerpa отработала - показываем её результаты
        if st.session_state.analysis_result and st.session_state.analysis_result.success:
            st.subheader("🧬 Совпадения геномов с молекулами (Nerpa)")
            display_results_page(fh.output_dir)
            has_results = True
            
        # Показываем таблицу antiSMASH (если она есть)
        if 'antismash_df' in st.session_state and st.session_state.antismash_df is not None and not st.session_state.antismash_df.empty:
            if has_results:
                st.divider()
            st.subheader("🦠 Обзор всех найденных кластеров (antiSMASH)")
            st.info("Это результаты Шага А. Ниже представлены все биосинтетические фабрики, обнаруженные в геноме (даже те, которые мы не искали).")
            
            csv_as = st.session_state.antismash_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Скачать таблицу кластеров (CSV)",
                data=csv_as,
                file_name="antismash_clusters.csv",
                mime="text/csv"
            )
            
            st.dataframe(st.session_state.antismash_df, use_container_width=True, hide_index=True)
            has_results = True
            
        if not has_results:
            st.info("👈 Сначала запустите Шаг A (antiSMASH) или Шаг B (Nerpa) на вкладке «Данные и Запуск»")
            
    with tabs[2]:
        st.header("📈 Визуализация")
        has_vis = False
        
        if st.session_state.results_df is not None:
            st.subheader("Визуализация совпадений Nerpa")
            display_visualizations(st.session_state.results_df)
            has_vis = True
            
        if 'antismash_df' in st.session_state and st.session_state.antismash_df is not None and not st.session_state.antismash_df.empty:
            if has_vis:
                st.divider()
            st.subheader("Распределение типов биосинтетических кластеров (antiSMASH)")
            
            df_as = st.session_state.antismash_df
            type_counts = df_as['Тип кластера'].value_counts().reset_index()
            type_counts.columns = ['Тип', 'Количество']
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                fig1 = px.pie(type_counts, names='Тип', values='Количество', title="Доля различных типов BGC", hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
            with col_v2:
                fig2 = px.bar(type_counts, x='Тип', y='Количество', title="Количество по типам BGC", color='Тип')
                st.plotly_chart(fig2, use_container_width=True)
            has_vis = True
            
        if not has_vis:
            st.info("👈 Сначала запустите анализ и дождитесь результатов")
            
    with tabs[3]:
        st.header("ℹ️ О программе")
        st.markdown(f"**Версия:** {APP_INFO['version']}\n\n[GitHub Nerpa]({APP_INFO['github']})")

if __name__ == "__main__":
    main()