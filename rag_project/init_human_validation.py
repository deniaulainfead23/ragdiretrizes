from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "analysis" / "official_run_20260912"
OUT = RUN / "human_validation"
OUT.mkdir(parents=True, exist_ok=True)

FILE = OUT / "validated_findings.csv"

COLUMNS = [
    "finding_id",
    "question_id",
    "country",
    "finding_type",
    "finding_source",
    "original_claim",
    "curated_claim",
    "evidence_ids",
    "document_ids",
    "pages",
    "validation_status",
    "validator_notes",
    "validated_at",
]

if FILE.exists():
    print("Arquivo já existe; nada foi sobrescrito:", FILE)
else:
    pd.DataFrame(columns=COLUMNS).to_csv(FILE, index=False, encoding="utf-8-sig")
    print("Arquivo criado:", FILE)

print("\nStatus permitidos: validated | reformulated | rejected")
print("Tipos sugeridos: convergence | difference | recurring_pattern | evidence_gap | country_finding")
print("Fontes sugeridas: model_comparison | researcher_observation | new_evidence")
