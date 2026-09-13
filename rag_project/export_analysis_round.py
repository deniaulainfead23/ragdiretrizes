from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "analysis" / "official_run_20260912"
OUT = RUN / "review_exports"
QUESTIONS = [f"Q{i:02d}" for i in range(1, 14)]
COUNTRIES = [
    "africa-do-sul","australia","brasil","canada","chile","china",
    "coreia-do-sul","estonia","eua","finlandia","gana","hong-kong",
    "irlanda","japao","nova-zelandia","quenia","reino-unido","ruanda",
    "singapura","suica","taiwan","uruguai"
]

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "questions").mkdir(exist_ok=True)
(OUT / "countries").mkdir(exist_ok=True)

responses = []
evidence = []

for country in COUNTRIES:
    r = pd.read_csv(RUN / country / "respostas.csv")
    e = pd.read_csv(RUN / country / "evidencias.csv")
    r["country"] = country
    e["country"] = country
    responses.append(r)
    evidence.append(e)

responses = pd.concat(responses, ignore_index=True)
evidence = pd.concat(evidence, ignore_index=True)
responses = responses[responses["question_id"].astype(str).isin(QUESTIONS)].copy()
evidence = evidence[evidence["question_id"].astype(str).isin(QUESTIONS)].copy()

for qid in QUESTIONS:
    responses[responses["question_id"].astype(str).eq(qid)].sort_values("country").to_csv(
        OUT / "questions" / f"{qid}.csv", index=False, encoding="utf-8-sig"
    )

for country in COUNTRIES:
    responses[responses["country"].eq(country)].sort_values("question_id").to_csv(
        OUT / "countries" / f"{country}.csv", index=False, encoding="utf-8-sig"
    )

manifest = {
    "official_run": RUN.name,
    "countries": len(COUNTRIES),
    "questions": len(QUESTIONS),
    "responses": int(len(responses)),
    "evidences": int(len(evidence)),
    "candidate": int((responses["validation_status"].astype(str).str.lower() == "candidate").sum()),
    "inconclusive": int((responses["validation_status"].astype(str).str.lower() == "inconclusive").sum()),
    "question_exports": 13,
    "country_exports": 22,
    "q14_input_exists": (RUN / "comparison" / "q14_input.csv").exists(),
    "q14_by_question_exists": (RUN / "comparison" / "q14_by_question.csv").exists(),
    "q14_final_v3_exists": (RUN / "comparison" / "q14_final_v3.json").exists(),
}

(OUT / "ANALYSIS_ROUND_MANIFEST.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
)

print("=== RODADA DE ANALISE EXPORTADA ===")
for key, value in manifest.items():
    print(f"{key}: {value}")
print("Saida:", OUT)
