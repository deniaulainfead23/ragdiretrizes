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

expected_questions = {f"Q{i:02d}" for i in range(1, 14)}

problems = []

total_responses = 0
total_evidence = 0
candidate = 0
inconclusive = 0

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

    candidate += (r["validation_status"].astype(str).str.lower() == "candidate").sum()
    inconclusive += (r["validation_status"].astype(str).str.lower() == "inconclusive").sum()

    found = set(r["question_id"].astype(str))
    missing = expected_questions - found

    if missing:
        problems.append(
            f"{country}: perguntas ausentes {sorted(missing)}"
        )

# arquivos comparativos
q14_input = COMP / "q14_input.csv"
q14_by_question = COMP / "q14_by_question.csv"
q14_final = COMP / "q14_final_v3.json"

for f in [q14_input, q14_by_question, q14_final]:
    if not f.exists():
        problems.append(f"arquivo ausente: {f.name}")

q14_input_rows = None
q14_theme_rows = None
q14_valid = False

if q14_input.exists():
    q = pd.read_csv(q14_input)
    q14_input_rows = len(q)

    if len(q) != 286:
        problems.append(
            f"q14_input.csv: esperado 286, encontrado {len(q)}"
        )

if q14_by_question.exists():
    q = pd.read_csv(q14_by_question)
    q14_theme_rows = len(q)

    if len(q) != 13:
        problems.append(
            f"q14_by_question.csv: esperado 13, encontrado {len(q)}"
        )

if q14_final.exists():
    try:
        data = json.loads(
            q14_final.read_text(encoding="utf-8")
        )

        result = data.get("result", {})

        q14_valid = (
            data.get("question_id") == "Q14"
            and isinstance(result, dict)
        )

        if not q14_valid:
            problems.append(
                "q14_final_v3.json: estrutura inválida"
            )

    except Exception as exc:
        problems.append(
            f"q14_final_v3.json: erro JSON {exc}"
        )

manifest = {
    "official_run": "official_run_20260912",
    "countries": len(COUNTRIES),
    "expected_responses": 22 * 13,
    "responses": int(total_responses),
    "candidate": int(candidate),
    "inconclusive": int(inconclusive),
    "evidences": int(total_evidence),
    "q14_input_rows": q14_input_rows,
    "q14_thematic_rows": q14_theme_rows,
    "q14_final_valid": q14_valid,
    "problems": problems,
}

out = RUN / "FINAL_RUN_MANIFEST.json"

out.write_text(
    json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print("\n=== FECHAMENTO DO PIPELINE ===")
print("Países:", len(COUNTRIES))
print("Respostas:", total_responses)
print("Esperado:", 22 * 13)
print("Candidates:", candidate)
print("Inconclusive:", inconclusive)
print("Evidências:", total_evidence)
print("Q14 input:", q14_input_rows)
print("Q14 temáticas:", q14_theme_rows)
print("Q14 final válido:", q14_valid)
print("Problemas:", len(problems))

if problems:
    print("\nPENDÊNCIAS:")
    for p in problems:
        print("-", p)
else:
    print("\nPIPELINE OFICIAL FECHADO: OK")

print("\nManifesto:", out)