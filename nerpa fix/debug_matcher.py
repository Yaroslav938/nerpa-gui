import subprocess
import os

def debug_matcher():
    print("🔍 Ищем NRPsMatcher...")
    
    # 1. Находим путь к файлу
    cmd_find = ["wsl", "-d", "Ubuntu-22.04", "find", "/home/yaroslav/miniconda3/envs/nerpa_wsl/", "-name", "NRPsMatcher"]
    res = subprocess.run(cmd_find, capture_output=True, text=True)
    
    paths = res.stdout.strip().splitlines()
    if not paths:
        print("❌ NRPsMatcher не найден! Установка Nerpa повреждена.")
        return

    matcher_path = paths[0]
    print(f"🎯 Найден: {matcher_path}")
    
    # 2. Проверяем права на выполнение
    print("🔧 Проверка прав запуска...")
    subprocess.run(["wsl", "-d", "Ubuntu-22.04", "ls", "-l", matcher_path])
    
    # Добавляем права на всякий случай
    subprocess.run(["wsl", "-d", "Ubuntu-22.04", "chmod", "+x", matcher_path])
    
    # 3. Тестовый запуск
    print("\n🚀 Пробуем запустить NRPsMatcher...")
    cmd_run = ["wsl", "-d", "Ubuntu-22.04", matcher_path, "--help"]
    
    res_run = subprocess.run(cmd_run, capture_output=True, text=True)
    
    print("=== STDOUT ===")
    print(res_run.stdout)
    print("=== STDERR ===")
    print(res_run.stderr)
    print(f"Код возврата: {res_run.returncode}")

    if res_run.returncode == 0 or "Usage" in res_run.stderr or "Options" in res_run.stdout:
        print("\n✅ NRPsMatcher работает исправно!")
    else:
        print("\n❌ NRPsMatcher НЕ ЗАПУСКАЕТСЯ.")
        print("Скорее всего, не хватает системных библиотек в WSL.")

if __name__ == "__main__":
    debug_matcher()
