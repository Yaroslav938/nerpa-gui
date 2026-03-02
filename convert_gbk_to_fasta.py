import os
from Bio import SeqIO  # Библиотека Biopython (уже есть в nerpa_wsl, но можно и в Windows)

# Папка с вашими GBK файлами
INPUT_DIR = r"C:\Users\user\AppData\Local\Temp\nerpa_gui_yf9m84f9\input"
OUTPUT_DIR = r"C:\Users\user\AppData\Local\Temp\nerpa_gui_yf9m84f9\input_fasta"

def convert():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"🔄 Конвертация GBK -> FASTA...")
    print(f"Исходная папка: {INPUT_DIR}")
    
    count = 0
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".gbk") or filename.endswith(".gb"):
            gbk_path = os.path.join(INPUT_DIR, filename)
            fasta_path = os.path.join(OUTPUT_DIR, filename.replace(".gbk", ".fasta").replace(".gb", ".fasta"))
            
            try:
                # Читаем GBK и пишем FASTA
                with open(gbk_path, "r") as input_handle:
                    sequences = SeqIO.parse(input_handle, "genbank")
                    count_seq = SeqIO.write(sequences, fasta_path, "fasta")
                
                if count_seq > 0:
                    print(f"  ✅ {filename} -> {os.path.basename(fasta_path)}")
                    count += 1
                else:
                    print(f"  ⚠️ {filename} пустой или битый.")
                    
            except Exception as e:
                print(f"  ❌ Ошибка с {filename}: {e}")

    print(f"\nГотово! Конвертировано {count} файлов.")
    print(f"Теперь выберите папку '{OUTPUT_DIR}' как входную в Nerpa GUI.")

if __name__ == "__main__":
    # Если нет Biopython в Windows, попробуем запустить через WSL
    try:
        import Bio
        convert()
    except ImportError:
        print("⚠️ В Windows нет Biopython. Запускаем через WSL...")
        # Генерируем временный скрипт для WSL
        script_content = f"""
import os
from Bio import SeqIO
input_dir = '{INPUT_DIR.replace(os.sep, '/').replace('C:', '/mnt/c')}'
output_dir = '{OUTPUT_DIR.replace(os.sep, '/').replace('C:', '/mnt/c')}'
if not os.path.exists(output_dir): os.makedirs(output_dir)
for f in os.listdir(input_dir):
    if f.endswith('.gbk'):
        SeqIO.write(SeqIO.parse(f'{{input_dir}}/{{f}}', 'genbank'), f'{{output_dir}}/{{f.replace(".gbk", ".fasta")}}', 'fasta')
print("Done inside WSL")
"""
        with open("temp_convert.py", "w") as f:
            f.write(script_content)
            
        os.system("wsl -d Ubuntu-22.04 python3 temp_convert.py")
        os.remove("temp_convert.py")
