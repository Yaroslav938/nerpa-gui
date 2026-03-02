import subprocess
import sys
import re

# Настройки поиска (ищем в окружении conda)
SEARCH_DIR = "/home/yaroslav/miniconda3/envs/nerpa_wsl/lib"
SEARCH_QUERY = "rBAN-1.0.jar"

def run_wsl(cmd):
    """Запускает команду в WSL и возвращает вывод."""
    full_cmd = ["wsl", "-d", "Ubuntu-22.04", "bash", "-c", cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    return res.stdout.strip()

def apply_patch():
    print("🔍 Поиск файла конфигурации rBAN внутри WSL...")
    
    # 1. Ищем файл, в котором упоминается rBAN-1.0.jar
    # Это найдет .py файл, который отвечает за запуск
    find_cmd = f"find {SEARCH_DIR} -name '*.py' -print0 | xargs -0 grep -l '{SEARCH_QUERY}'"
    target_file = run_wsl(find_cmd)
    
    if not target_file:
        print("❌ Не удалось найти файл, запускающий rBAN.")
        print("Попробуйте найти его вручную командой в WSL: grep -r 'rBAN-1.0.jar' ~/")
        return

    # Если нашлось несколько файлов, берем первый (обычно он один)
    target_file = target_file.split('\n')[0]
    print(f"📄 Найден файл: {target_file}")
    
    # 2. Читаем файл
    print("📖 Чтение файла...")
    content = run_wsl(f"cat '{target_file}'")
    
    if "-Xss100m" in content:
        print("✅ Патч уже применен! Ничего делать не нужно.")
        return

    # 3. Делаем бэкап
    print("💾 Создание резервной копии...")
    run_wsl(f"cp '{target_file}' '{target_file}.bak'")
    
    # 4. Применяем патч (замена строки запуска)
    # Ищем варианты: ['java', '-jar' ...] или "java -jar ..."
    
    new_content = content
    patched = False
    
    # Вариант 1: Список аргументов (самый вероятный для Python subprocess)
    # Заменяем ['java', '-jar' на ['java', '-Xss100m', '-jar'
    if "['java', '-jar'" in new_content:
        new_content = new_content.replace("['java', '-jar'", "['java', '-Xss100m', '-jar'")
        patched = True
    elif '["java", "-jar"' in new_content:
        new_content = new_content.replace('["java", "-jar"', '["java", "-Xss100m", "-jar"')
        patched = True
        
    # Вариант 2: Строка (редко, но бывает)
    elif "java -jar" in new_content:
        new_content = new_content.replace("java -jar", "java -Xss100m -jar")
        patched = True
        
    if not patched:
        print("⚠️ Не удалось найти точное место для вставки флага.")
        print("Содержимое файла (первые 500 символов):")
        print(content[:500])
        return

    # 5. Записываем обратно
    print("✏️ Запись исправленного файла...")
    # Используем printf чтобы избежать проблем с экранированием при передаче через bash
    # Но проще записать через временный файл в /tmp
    
    try:
        # Пишем во временный файл в Windows, потом копируем в WSL path
        # Это сложно из-за путей. Проще передать через pipe.
        
        # Экранируем одинарные кавычки для bash
        safe_content = new_content.replace("'", "'\\''")
        
        write_cmd = f"echo '{safe_content}' > '{target_file}'"
        # Для надежности используем python внутри wsl для записи, чтобы не ломать кодировку
        
        python_writer = f"""
import sys
with open('{target_file}', 'w') as f:
    f.write(sys.stdin.read())
"""
        subprocess.run(["wsl", "-d", "Ubuntu-22.04", "python3", "-c", python_writer], input=new_content, text=True)
        
        print("✅ УСПЕХ! Патч применен.")
        print("Теперь rBAN будет запускаться с увеличенной памятью.")
        
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")

if __name__ == "__main__":
    apply_patch()
