import os
import sys

# ВАШ ПУТЬ
NERPA_PATH = r"\\wsl.localhost\Ubuntu-22.04\home\yaroslav\miniconda3\envs\nerpa_wsl\bin\nerpa.py"

def apply_fix_v10():
    print(f"🔍 Путь: {NERPA_PATH}")
    if not os.path.exists(NERPA_PATH):
        print("❌ Файл не найден!")
        return

    bin_dir = os.path.dirname(NERPA_PATH)
    target_file = os.path.abspath(os.path.join(bin_dir, "../share/nerpa/nerpa_pipeline/NRPSPredictor_utils/json_handler.py"))
    
    print(f"📂 Целевой файл: {target_file}")
    if not os.path.exists(target_file):
        print("❌ json_handler.py не найден.")
        return

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("🔧 Исправляю типы данных (list -> str)...")
    
    # ВАЖНО: Мы меняем дефолтное значение с [] на 'UNKNOWN' или ''
    # Для метода __str__ все поля должны быть строками!
    
    replacements = [
        # === Исправляем старые патчи (где мы ставили []) ===
        # Меняем .get(..., []) на .get(..., 'UNKNOWN')
        
        (".get('large_cluster_predictions', [])", ".get('large_cluster_predictions', 'UNKNOWN')"),
        (".get('small_cluster_predictions', [])", ".get('small_cluster_predictions', 'UNKNOWN')"),
        (".get('single_cluster_predictions', [])", ".get('single_cluster_predictions', 'UNKNOWN')"),
        
        (".get('large_cluster_pred', [])", ".get('large_cluster_pred', 'UNKNOWN')"),
        (".get('small_cluster_pred', [])", ".get('small_cluster_pred', 'UNKNOWN')"),
        (".get('single_cluster_pred', [])", ".get('single_cluster_pred', 'UNKNOWN')"),

        (".get('large_amino_pred', [])", ".get('large_amino_pred', 'UNKNOWN')"),
        (".get('small_amino_pred', [])", ".get('small_amino_pred', 'UNKNOWN')"),
        (".get('single_amino_pred', [])", ".get('single_amino_pred', 'UNKNOWN')"),

        # Для uncertain тоже лучше строку, если оно пишется в файл
        (".get('uncertain', [])", ".get('uncertain', 'UNKNOWN')"),
        
        # === Если патчи еще не применены (на всякий случай) ===
        ("['large_cluster_pred']", ".get('large_cluster_pred', 'UNKNOWN')"),
        ("['small_cluster_pred']", ".get('small_cluster_pred', 'UNKNOWN')"),
        ("['single_cluster_pred']", ".get('single_cluster_pred', 'UNKNOWN')"),
        ("['single_amino_pred']", ".get('single_amino_pred', 'UNKNOWN')"),
        ("['uncertain']", ".get('uncertain', 'UNKNOWN')"),
    ]

    new_content = content
    count = 0
    for old, new in replacements:
        if old in new_content:
            new_content = new_content.replace(old, new)
            count += 1
    
    new_content += "\n# PATCHED_FINAL_V10_TYPES"

    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ Успешно! Типы данных исправлены ({count} замен).")
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")

if __name__ == "__main__":
    apply_fix_v10()
