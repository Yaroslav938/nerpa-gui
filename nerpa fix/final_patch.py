import subprocess
import os

# Ищем во всем окружении, а не только в lib
SEARCH_ROOT = "/home/yaroslav/miniconda3/envs/nerpa_wsl/"

def run_wsl_cmd(cmd):
    result = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "bash", "-c", cmd], capture_output=True, text=True)
    return result.stdout.strip()

def final_patch():
    print("🕵️‍♂️ Глобальный поиск файла с кодом rBAN...")
    
    # 1. Ищем файл, содержащий строку "rBAN-1.0.jar" или просто "rBAN"
    # Исключаем бинарные файлы и папки pycache
    # grep -r "text" path
    print("⏳ Это может занять секунд 10-20...")
    
    # Сначала ищем точное совпадение с именем JAR файла
    cmd_find = f"grep -r 'rBAN-1.0.jar' {SEARCH_ROOT} | grep '.py:'"
    output = run_wsl_cmd(cmd_find)
    
    if not output:
        print("⚠️ Точное имя JAR не найдено в коде. Ищем просто 'rBAN'...")
        cmd_find = f"grep -r 'rBAN' {SEARCH_ROOT} | grep '.py:' | grep -v 'site-packages/pip'"
        output = run_wsl_cmd(cmd_find)

    if not output:
        print("❌ Файл не найден! Это мистика. Возможно код скомпилирован (.pyc).")
        return

    # Разбираем результаты
    candidates = []
    for line in output.splitlines():
        parts = line.split(":", 1)
        if len(parts) == 2:
            fpath = parts[0].strip()
            # Берем только файлы, которые выглядят как код Nerpa
            if "nerpa" in fpath and fpath.endswith(".py"):
                candidates.append(fpath)

    # Убираем дубликаты
    candidates = list(set(candidates))
    
    if not candidates:
        print("❌ Найдены совпадения, но это не похоже на код Nerpa.")
        print(output[:500])
        return

    target_file = candidates[0]
    # Если файлов несколько, пытаемся найти самый "глубокий" (обычно это исходник)
    # или тот, который содержит 'wrapper' или 'runner'
    for c in candidates:
        if "nerpa_pipeline" in c: 
            target_file = c
            break

    print(f"🎯 ЦЕЛЬ ОБНАРУЖЕНА: {target_file}")
    
    # 2. Читаем файл
    print("📖 Чтение кода...")
    content = run_wsl_cmd(f"cat '{target_file}'")
    
    if "-Xss100m" in content:
        print("✅ Этот файл уже пропатчен!")
        return

    # 3. Применяем патч
    print("🛠️ Применяем патч...")
    new_content = content
    patched = False

    # Логика замены:
    # Ищем список аргументов. Обычно там есть ['java', '-jar', ...]
    # Или construction of cmd list.
    
    # Самый надежный способ: найти "-jar" и вставить перед ним "-Xss100m"
    if "'-jar'" in new_content:
        new_content = new_content.replace("'-jar'", "'-Xss100m', '-jar'")
        patched = True
    elif '"-jar"' in new_content:
        new_content = new_content.replace('"-jar"', '"-Xss100m", "-jar"')
        patched = True
    elif "java -jar" in new_content: # Если строка
        new_content = new_content.replace("java -jar", "java -Xss100m -jar")
        patched = True
        
    if not patched:
        print("⚠️ Не удалось автоматически найти место для вставки.")
        print("Попробуйте прислать мне содержимое этого файла, я скажу, что заменить.")
        print(f"Файл: {target_file}")
        return

    # 4. Сохраняем (через временный файл Python в WSL чтобы не бить кодировку)
    print("💾 Сохранение...")
    
    # Создаем скрипт-писатель внутри WSL
    saver_script = f"""
import sys
target = '{target_file}'
content = sys.stdin.read()
# Делаем бэкап
import shutil
shutil.copy(target, target + '.bak')
# Пишем
with open(target, 'w') as f:
    f.write(content)
print('Done')
"""
    # Запускаем python внутри WSL, передаем новый код через stdin
    try:
        p = subprocess.run(
            ["wsl", "-d", "Ubuntu-22.04", "python3", "-c", saver_script],
            input=new_content,
            text=True,
            capture_output=True
        )
        if "Done" in p.stdout:
            print("✅ УСПЕХ! Файл успешно пропатчен.")
            print("Теперь Nerpa должна работать стабильно.")
        else:
            print("❌ Ошибка при сохранении:")
            print(p.stderr)
            print(p.stdout)
    except Exception as e:
        print(f"Error saving: {e}")

if __name__ == "__main__":
    final_patch()
