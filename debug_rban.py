import os
import sys
import subprocess

NERPA_PATH = r"\\wsl.localhost\Ubuntu-22.04\home\yaroslav\miniconda3\envs\nerpa_wsl\bin\nerpa.py"
# ВСТАВЬТЕ СЮДА ПУТЬ ИЗ POSLEDNEGO LOGA (C:\Users\...\output)
OUTPUT_DIR = r"C:\Users\user\AppData\Local\Temp\nerpa_gui_avy0gulp\output"

def to_wsl(path):
    # Превращаем C:\... в /mnt/c/...
    drive, tail = os.path.splitdrive(path)
    if drive:
        return f"/mnt/{drive[0].lower()}{tail.replace(os.sep, '/')}"
    return path.replace('\\', '/')

def debug_rban_direct():
    print("🔍 Прямой запуск rBAN через WSL...")
    
    # 1. Путь к JAR (Linux format)
    # /home/yaroslav/.../share/nerpa/external_tools/rBAN/rBAN-1.0.jar
    # Мы знаем его из find
    linux_jar = "/home/yaroslav/miniconda3/envs/nerpa_wsl/share/nerpa/external_tools/rBAN/rBAN-1.0.jar"
    
    # 2. Пути к файлам (Linux format /mnt/c/...)
    wsl_input = to_wsl(os.path.join(OUTPUT_DIR, "rban.input.json"))
    wsl_output = to_wsl(OUTPUT_DIR) + "/"
    wsl_db = to_wsl(os.path.join(OUTPUT_DIR, "rban_monomers_db.json"))
    
    # 3. Команда
    cmd = [
        "wsl", "-d", "Ubuntu-22.04",
        "java", "-jar", linux_jar,
        "-inputFile", wsl_input,
        "-outputFolder", wsl_output,
        "-outputFileName", "debug.json",
        "-monomersDB", wsl_db
    ]
    
    print(f"\n🚀 CMD:\n{' '.join(cmd)}\n")
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        print("=== STDOUT ===")
        print(res.stdout)
        print("=== STDERR ===")
        print(res.stderr)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_rban_direct()
