from pathlib import Path
import json
import os
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "analysis" / "official_run_20260912"
INPUT = RUN / "comparison" / "q14_validated_input.csv"
OUTPUT = RUN / "comparison" / "q14_validated_final.json"

load_dotenv(ROOT / "rag_project" / ".env")

if not INPUT.exists():
    raise SystemExit("Entrada validada ausente. Rode: python -m rag_project.build_q14_validated_input")

df = pd.read_csv(INPUT, dtype=str).fillna("")
if df.empty:
    raise SystemExit("Ainda não há achados validados/reformulados para compor a Q14.")

records = df.to_dict("records")

prompt = f"""
Você está produzindo a síntese comparativa Q14 de uma pesquisa documental internacional sobre Computação e Educação Digital.

Use EXCLUSIVAMENTE os achados validados ou reformulados pela pesquisadora fornecidos abaixo.

REGRAS:
1. Não use conhecimento externo.
2. Não volte ao corpus bruto.
3. Não use achados rejeitados.
4. Não invente países, perguntas-fonte ou evidências.
5. Não interprete ausência de recuperação como ausência conceitual.
6. Não faça ranking entre países.
7. Não faça afirmações sobre efetividade, impacto ou implementação observada.
8. Preserve a distinção entre convergência, diferença, padrão recorrente, lacuna de evidência e achado nacional.
9. Toda afirmação deve ser rastreável aos finding_id e question_id fornecidos.
10. Se os achados validados forem insuficientes para uma síntese ampla, declare a limitação explicitamente.

Responda SOMENTE em JSON válido no formato:
{{
  "question_id": "Q14",
  "synthesis": "",
  "major_convergences": [
    {{"claim": "", "countries": [], "source_questions": [], "finding_ids": []}}
  ],
  "major_differences": [
    {{"claim": "", "countries": [], "source_questions": [], "finding_ids": []}}
  ],
  "recurring_patterns": [
    {{"claim": "", "countries": [], "source_questions": [], "finding_ids": []}}
  ],
  "evidence_gaps": [
    {{"claim": "", "countries": [], "source_questions": [], "finding_ids": []}}
  ],
  "limitations": []
}}

ACHADOS VALIDADOS:
{json.dumps(records, ensure_ascii=False)}
"""

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
response = client.responses.create(
    model=os.environ.get("OPENAI_Q14_MODEL", "gpt-4o-mini"),
    input=prompt,
)
raw = response.output_text.strip()
if raw.startswith("```"):
    raw = raw.replace("```json", "", 1).replace("```", "").strip()
result = json.loads(raw)

payload = {
    "question_id": "Q14",
    "prompt_version": "q14-human-validated-v1.0",
    "source_file": str(INPUT.relative_to(ROOT)),
    "validated_findings_count": int(len(df)),
    "result": result,
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

print("=== Q14 A PARTIR DE ACHADOS VALIDADOS ===")
print("Achados usados:", len(df))
print("Arquivo:", OUTPUT)
print("Síntese:", result.get("synthesis", ""))
