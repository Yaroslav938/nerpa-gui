import subprocess
import os

# ПУТЬ К ПОСЛЕДНЕМУ ЗАПУСКУ (из лога)
OUTPUT_DIR = r"C:\Users\user\AppData\Local\Temp\nerpa_gui_yf9m84f9\output"
INPUT_DIR = r"C:\Users\user\AppData\Local\Temp\nerpa_gui_yf9m84f9\input"
TSV_FILE = r"C:\Users\user\AppData\Local\Temp\nerpa_gui_yf9m84f9\input\mibig_norine_fixed.tsv"

def to_wsl(path):
    drive, tail = os.path.splitdrive(path)
    if drive:
        return f"/mnt/{drive[0].lower()}{tail.replace(os.sep, '/')}"
    return path.replace('\\', '/')

def trace_nerpa():
    print("🐞 Трассировка запуска Nerpa...")
    
    wsl_out = to_wsl(OUTPUT_DIR)
    wsl_in = to_wsl(INPUT_DIR)
    wsl_tsv = to_wsl(TSV_FILE)
    
    # Команда запуска с модулем trace
    # python -m trace --trace script.py ...
    
    cmd = [
        "wsl", "-d", "Ubuntu-22.04",
        "/home/yaroslav/miniconda3/envs/nerpa_wsl/bin/python",
        "-m", "trace", "--trace",  # <--- Включаем трассировку!
        "/home/yaroslav/miniconda3/envs/nerpa_wsl/bin/nerpa.py",
        "-a", wsl_in,
        "-o", wsl_out,
        "--smiles-tsv", wsl_tsv,
        "--process-hybrids",
        "--threads", "4",
        "--force-existing-outdir"
    ]
    
    print("\n🚀 ЗАПУСК (Это будет много текста!)...")
    
    # Записываем вывод в файл, потому что его будет МНОГО
    log_file = "nerpa_trace.log"
    with open(log_file, "w") as f_log:
        subprocess.run(cmd, stdout=f_log, stderr=subprocess.STDOUT, text=True)
        
    print(f"\n✅ Трассировка завершена. Лог сохранен в {log_file}")
    
    # Читаем последние 50 строк лога (где произошла ошибка)
    print("\n=== ПОСЛЕДНИЕ СТРОКИ ЛОГА ===")
    with open(log_file, "r") as f:
        lines = f.readlines()
        for line in lines[-50:]:
            print(line.strip())

if __name__ == "__main__":
    trace_nerpa()
