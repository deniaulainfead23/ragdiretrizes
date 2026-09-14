from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "analysis" / "official_run_20260912"
QUESTIONS_DIR = RUN / "review_exports" / "questions"

COUNTRIES = [
    "africa-do-sul","australia","brasil","canada","chile","china",
    "coreia-do-sul","estonia","eua","finlandia","gana","hong-kong",
    "irlanda","japao","nova-zelandia","quenia","reino-unido","ruanda",
    "singapura","suica","taiwan","uruguai"
]
QUESTIONS = [f"Q{i:02d}" for i in range(1, 14)]

problems = []
checked = 0

for country in COUNTRIES:
    source_file = RUN / country / "respostas.csv"
    if not source_file.exists():
        problems.append((country, "*", "SOURCE_MISSING", str(source_file), ""))
        continue

    source = pd.read_csv(source_file)
    for qid in QUESTIONS:
        src = source[source["question_id"].astype(str).eq(qid)]
        if len(src) != 1:
            problems.append((country, qid, "SOURCE_ROW_COUNT", str(source_file), str(len(src))))
            continue

        qfile = QUESTIONS_DIR / f"{qid}.csv"
        if not qfile.exists():
            problems.append((country, qid, "EXPORT_MISSING", str(qfile), ""))
            continue

        exported = pd.read_csv(qfile)
        exp = exported[exported["country"].astype(str).eq(country)]
        if len(exp) != 1:
            problems.append((country, qid, "EXPORT_ROW_COUNT", str(qfile), str(len(exp))))
            continue

        src_response = src.iloc[0].get("response", "")
        exp_response = exp.iloc[0].get("response", "")
        src_text = "" if pd.isna(src_response) else str(src_response).strip()
        exp_text = "" if pd.isna(exp_response) else str(exp_response).strip()
        checked += 1

        if src_text != exp_text:
            problems.append((country, qid, "EXPORT_DIFFERS_FROM_SOURCE", str(qfile), ""))

        # Detecta resposta vazia ou conteúdo que parece JSON bruto de resposta do modelo.
        if not src_text:
            problems.append((country, qid, "EMPTY_RESPONSE_IN_SOURCE", str(source_file), ""))
            continue

        if src_text.startswith("{") and src_text.endswith("}"):
            try:
                obj = json.loads(src_text)
                nested_response = obj.get("response") if isinstance(obj, dict) else None
                detail = f"nested_response={nested_response!r}" if isinstance(obj, dict) else "json_non_dict"
                problems.append((country, qid, "RAW_JSON_IN_SOURCE_RESPONSE", str(source_file), detail))
            except Exception:
                problems.append((country, qid, "JSON_LIKE_TEXT_IN_SOURCE_RESPONSE", str(source_file), "parse_failed"))

print("=== AUDITORIA MATRIZ CONSOLIDADA ===")
print("Pares verificados:", checked)
print("Problemas:", len(problems))

if problems:
    print("\ncountry,question_id,problem,file,detail")
    for row in problems:
        print(",".join(str(x).replace("\n", " ") for x in row))
else:
    print("OK: exports reproduzem exatamente respostas.csv e não foram encontrados JSONs brutos/respostas vazias.")

# Diagnóstico explícito do caso Brasil/Q04.
country = "brasil"
qid = "Q04"
source_file = RUN / country / "respostas.csv"
qfile = QUESTIONS_DIR / f"{qid}.csv"
print("\n=== DIAGNÓSTICO BRASIL Q04 ===")
if source_file.exists():
    source = pd.read_csv(source_file)
    src = source[source["question_id"].astype(str).eq(qid)]
    if len(src) == 1:
        print("Fonte respostas.csv -> response:")
        print(src.iloc[0].get("response", ""))
        print("Fonte validation_status:", src.iloc[0].get("validation_status", ""))
if qfile.exists():
    exported = pd.read_csv(qfile)
    exp = exported[exported["country"].astype(str).eq(country)]
    if len(exp) == 1:
        print("\nExport Q04.csv -> response:")
        print(exp.iloc[0].get("response", ""))
        print("Export validation_status:", exp.iloc[0].get("validation_status", ""))
