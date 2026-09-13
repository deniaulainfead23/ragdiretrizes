from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "analysis" / "official_run_20260912"
COMP = RUN / "comparison"

COUNTRIES = [
    "africa-do-sul","australia","brasil","canada","chile","china",
    "coreia-do-sul","estonia","eua","finlandia","gana","hong-kong",
    "irlanda","japao","nova-zelandia","quenia","reino-unido","ruanda",
    "singapura","suica","taiwan","uruguai"
]
EXPECTED = {f"Q{i:02d}" for i in range(1, 14)}

problems = []
total_responses = total_evidence = candidate = inconclusive = 0

for country in COUNTRIES:
    rfile = RUN / country / "respostas.csv"
    efile = RUN / country / "evidencias.csv"
    if not rfile.exists():
        problems.append(f"{country}: respostas.csv ausente")
        continue
    if not efile.exists():
        problems.append(f"{country}: evidencias.csv ausente")
        continue

    r = pd.read_csv(rfile)
    e = pd.read_csv(efile)
    total_responses += len(r)
    total_evidence += len(e)
    status = r["validation_status"].astype(str).str.lower()
    candidate += int((status == "candidate").sum())
    inconclusive += int((status == "inconclusive").sum())
    missing = EXPECTED - set(r["question_id"].astype(str))
    if missing:
        problems.append(f"{country}: perguntas ausentes {sorted(missing)}")

q14_input = COMP / "q14_input.csv"
q14_by_question = COMP / "q14_by_question.csv"
q14_final_candidates = [COMP / "q14_final_v3.json", COMP / "q14_final_v2.json", COMP / "q14_final.json"]
q14_final = next((p for p in q14_final_candidates if p.exists()), None)

q14_input_rows = None
q14_theme_rows = None
q14_valid = False

if not q14_input.exists():
    problems.append("q14_input.csv ausente")
else:
    q14_input_rows = len(pd.read_csv(q14_input))
    if q14_input_rows != 286:
        problems.append(f"q14_input.csv: esperado 286, encontrado {q14_input_rows}")

if not q14_by_question.exists():
    problems.append("q14_by_question.csv ausente")
else:
    q14_theme_rows = len(pd.read_csv(q14_by_question))
    if q14_theme_rows != 13:
        problems.append(f"q14_by_question.csv: esperado 13, encontrado {q14_theme_rows}")

if q14_final is None:
    problems.append("Q14 final ausente")
else:
    try:
        data = json.loads(q14_final.read_text(encoding="utf-8"))
        q14_valid = data.get("question_id") == "Q14" and isinstance(data.get("result"), dict)
        if not q14_valid:
            problems.append(f"{q14_final.name}: estrutura inválida")
    except Exception as exc:
        problems.append(f"{q14_final.name}: erro JSON {exc}")

manifest = {
    "official_run": RUN.name,
    "countries": len(COUNTRIES),
    "expected_responses": 286,
    "responses": int(total_responses),
    "candidate": int(candidate),
    "inconclusive": int(inconclusive),
    "evidences": int(total_evidence),
    "q14_input_rows": q14_input_rows,
    "q14_thematic_rows": q14_theme_rows,
    "q14_final_selected": q14_final.name if q14_final else None,
    "q14_final_valid": q14_valid,
    "problems": problems,
}

out = RUN / "FINAL_RUN_MANIFEST.json"
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

print("=== FECHAMENTO DO PIPELINE ===")
print("Países:", len(COUNTRIES))
print("Respostas:", total_responses)
print("Esperado:", 286)
print("Candidates:", candidate)
print("Inconclusive:", inconclusive)
print("Evidências:", total_evidence)
print("Q14 input:", q14_input_rows)
print("Q14 temáticas:", q14_theme_rows)
print("Q14 final válido:", q14_valid)
print("Problemas:", len(problems))
if problems:
    print("\nPENDÊNCIAS:")
    for problem in problems:
        print("-", problem)
else:
    print("\nPIPELINE OFICIAL FECHADO: OK")
print("\nManifesto:", out)
