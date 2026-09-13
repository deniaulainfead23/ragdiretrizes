from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "analysis" / "official_run_20260912"
SRC = RUN / "human_validation" / "validated_findings.csv"
OUTDIR = RUN / "comparison"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / "q14_validated_input.csv"
AUDIT = OUTDIR / "q14_validated_input_audit.json"

VALID_STATUSES = {"validated", "reformulated"}
VALID_TYPES = {"convergence", "difference", "recurring_pattern", "evidence_gap", "country_finding"}
VALID_QUESTIONS = {f"Q{i:02d}" for i in range(1, 14)}
VALID_COUNTRIES = {
    "africa-do-sul","australia","brasil","canada","chile","china",
    "coreia-do-sul","estonia","eua","finlandia","gana","hong-kong",
    "irlanda","japao","nova-zelandia","quenia","reino-unido","ruanda",
    "singapura","suica","taiwan","uruguai"
}

if not SRC.exists():
    raise SystemExit("Arquivo de validação humana não existe. Rode: python -m rag_project.init_human_validation")

df = pd.read_csv(SRC, dtype=str).fillna("")
issues = []

for i, row in df.iterrows():
    line = i + 2
    status = row.get("validation_status", "").strip().lower()
    qid = row.get("question_id", "").strip()
    country = row.get("country", "").strip()
    ftype = row.get("finding_type", "").strip()
    claim = row.get("curated_claim", "").strip()

    if status and status not in {"validated", "reformulated", "rejected"}:
        issues.append(f"linha {line}: validation_status inválido: {status}")
    if qid and qid not in VALID_QUESTIONS:
        issues.append(f"linha {line}: question_id inválido: {qid}")
    if country and country not in VALID_COUNTRIES:
        issues.append(f"linha {line}: country inválido: {country}")
    if ftype and ftype not in VALID_TYPES:
        issues.append(f"linha {line}: finding_type inválido: {ftype}")
    if status in VALID_STATUSES and not claim:
        issues.append(f"linha {line}: curated_claim obrigatório para {status}")
    if status in VALID_STATUSES and not row.get("finding_id", "").strip():
        issues.append(f"linha {line}: finding_id obrigatório")

selected = df[df["validation_status"].str.lower().isin(VALID_STATUSES)].copy()
if not selected.empty:
    selected = selected.sort_values(["question_id", "country", "finding_type", "finding_id"])
selected.to_csv(OUT, index=False, encoding="utf-8-sig")

audit = {
    "source": str(SRC.relative_to(ROOT)),
    "rows_total": int(len(df)),
    "rows_validated_or_reformulated": int(len(selected)),
    "rows_rejected": int((df["validation_status"].str.lower() == "rejected").sum()),
    "questions_represented": sorted(selected["question_id"].dropna().unique().tolist()) if not selected.empty else [],
    "countries_represented": sorted([c for c in selected["country"].dropna().unique().tolist() if c]) if not selected.empty else [],
    "issues": issues,
}
AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

print("=== Q14 VALIDATED INPUT ===")
print("Linhas totais:", len(df))
print("Validadas/reformuladas:", len(selected))
print("Rejeitadas:", audit["rows_rejected"])
print("Problemas:", len(issues))
print("Arquivo:", OUT)
print("Auditoria:", AUDIT)
if issues:
    print("\nPENDÊNCIAS:")
    for issue in issues:
        print("-", issue)
