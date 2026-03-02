import json
import os

def create_test_data():
    smiles_content = "ID\tSMILES\nMock_DHB_Ser\tC1=CC(=C(C(=C1)C(=O)N[C@@H](CO)C(=O)O)O)O\n"
    with open("test_smiles.tsv", "w", encoding="utf-8") as f:
        f.write(smiles_content)

    # ИДЕАЛЬНЫЙ GBK (Убрали строчку sec_met_domain, из-за которой падал парсер)
    origin_seq = "atgc" * 750  # 3000 bp
    origin_lines = [f"{i+1:9d} " + " ".join([origin_seq[i:i+60][j:j+10] for j in range(0, len(origin_seq[i:i+60]), 10)]) for i in range(0, len(origin_seq), 60)]
    origin_text = "\n".join(origin_lines)

    gbk_content = f"""LOCUS       ctg1                    3000 bp    DNA     linear   BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     region          1..3000
                     /product="NRPS"
                     /region_number="1"
     CDS             100..2500
                     /locus_tag="ctg1_1"
     aSDomain        100..200
                     /aSDomain="Condensation"
                     /locus_tag="ctg1_1"
     aSDomain        200..400
                     /aSDomain="AMP-binding"
                     /locus_tag="ctg1_1"
                     /domain_id="nrpspksdomains_ctg1_1_AMP1"
                     /specificity="consensus: dhb"
                     /specificity="NRPspredictor2: dhb"
                     /specificity="nrpsPredictor2: dhb"
     aSDomain        400..500
                     /aSDomain="PCP"
                     /locus_tag="ctg1_1"
     aSDomain        600..700
                     /aSDomain="Condensation"
                     /locus_tag="ctg1_1"
     aSDomain        700..900
                     /aSDomain="AMP-binding"
                     /locus_tag="ctg1_1"
                     /domain_id="nrpspksdomains_ctg1_1_AMP2"
                     /specificity="consensus: ser"
                     /specificity="NRPspredictor2: ser"
                     /specificity="nrpsPredictor2: ser"
     aSDomain        900..1000
                     /aSDomain="PCP"
                     /locus_tag="ctg1_1"
     aSDomain        1000..1100
                     /aSDomain="Thioesterase"
                     /locus_tag="ctg1_1"
ORIGIN
{origin_text}
//
"""
    with open("test_genome.gbk", "w", encoding="utf-8") as f:
        f.write(gbk_content)
        
    # Удалим JSON, чтобы он точно не путался под ногами
    if os.path.exists("test_genome.json"):
        os.remove("test_genome.json")

    print("✅ Успех! Созданы файлы: test_genome.gbk и test_smiles.tsv.")

if __name__ == "__main__":
    create_test_data()