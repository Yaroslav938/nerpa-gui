import subprocess

def find_rban():
    print("🔍 Сканирование окружения Nerpa в WSL...")
    
    # Ищем рекурсивно во всей папке lib (где лежат библиотеки python)
    # Ищем строку "rBAN" (она точно должна быть в коде, чтобы запустить JAR)
    cmd = [
        "wsl", "-d", "Ubuntu-22.04", 
        "grep", "-r", "rBAN", 
        "/home/yaroslav/miniconda3/envs/nerpa_wsl/lib/"
    ]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        lines = res.stdout.splitlines()
        
        found_files = set()
        for line in lines:
            # grep выдает: filename:match_text
            if ":matches" in line: continue # пропускаем бинарники
            parts = line.split(":", 1)
            if len(parts) == 2:
                fname = parts[0]
                if fname.endswith(".py"):
                    found_files.add(fname)
        
        if not found_files:
            print("❌ Ничего не найдено.")
            return

        print("\n📄 Найдены кандидаты:")
        for f in found_files:
            print(f)
            
        # Пытаемся угадать самый важный
        best_candidate = next((f for f in found_files if "rban" in f.lower() or "external" in f.lower()), None)
        
        if best_candidate:
            print(f"\n🎯 Вероятная цель: {best_candidate}")
            print("\nЧтение содержимого (первые 20 строк)...")
            subprocess.run(["wsl", "-d", "Ubuntu-22.04", "head", "-n", "20", best_candidate])
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_rban()
