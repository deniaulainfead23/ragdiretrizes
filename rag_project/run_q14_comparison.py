from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = (
    ROOT
    / "analysis"
    / "official_run_20260912"
    / "comparison"
    / "q14_input.csv"
)

DEFAULT_OUT = (
    ROOT
    / "analysis"
    / "official_run_20260912"
    / "comparison"
)

DEFAULT_MODEL = os.environ.get(
    "OPENAI_Q14_MODEL",
    "gpt-4o-mini"
)

PROMPT_VERSION = "q14-comparison-v1.0"


def safe_json(text):
    text = str(text or "").strip()

    if text.startswith("```"):
        text = (
            text.replace("```json", "", 1)
            .replace("```", "")
            .strip()
        )

    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def call_model(client, model, prompt):
    response = client.responses.create(
        model=model,
        input=prompt
    )
    return response.output_text


def run(input_csv, out_dir, model):

    df = pd.read_csv(input_csv)

    required = {
        "country",
        "question_id",
        "question_text",
        "response",
        "validation_status",
        "evidence_ids",
        "document_ids",
        "pages",
    }

    missing = sorted(required - set(df.columns))

    if missing:
        raise ValueError(
            f"Colunas ausentes: {missing}"
        )

    if len(df) != 286:
        raise ValueError(
            f"Esperadas 286 linhas; encontradas {len(df)}"
        )

    if df["country"].nunique() != 22:
        raise ValueError(
            "Número de países diferente de 22"
        )

    if df["question_id"].nunique() != 13:
        raise ValueError(
            "Número de perguntas diferente de 13"
        )

    out_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    thematic_rows = []

    for qid in sorted(
        df["question_id"].unique()
    ):

        part = df[
            df["question_id"].eq(qid)
        ].copy()

        records = part[
            [
                "country",
                "question_text",
                "response",
                "validation_status",
                "evidence_ids",
                "document_ids",
                "pages",
            ]
        ].to_dict("records")

        prompt = f"""
Você está executando a etapa Q14 de uma pesquisa
comparativa internacional sobre Computação e Educação Digital.

Compare SOMENTE os resultados nacionais fornecidos abaixo.

REGRAS METODOLÓGICAS:

1. Não use conhecimento externo.
2. Não consulte novamente o corpus bruto.
3. Não faça ranking de países.
4. Não use expressões como melhor, pior, mais avançado
   ou maior alinhamento.
5. Um resultado inconclusive significa apenas
   insuficiência de evidência recuperada.
6. Não interprete inconclusive como ausência do conceito
   no currículo do país.
7. Toda afirmação comparativa deve indicar os países
   sustentados pelos dados.
8. Diferencie:
   - convergências;
   - diferenças;
   - padrões recorrentes;
   - lacunas de evidência.
9. Não invente evidências.
10. Responda SOMENTE em JSON válido.

Formato obrigatório:

{{
  "question_id": "{qid}",
  "theme": "",
  "convergences": [
    {{
      "claim": "",
      "countries": []
    }}
  ],
  "differences": [
    {{
      "claim": "",
      "countries": []
    }}
  ],
  "recurring_patterns": [
    {{
      "claim": "",
      "countries": []
    }}
  ],
  "evidence_gaps": [
    {{
      "claim": "",
      "countries": []
    }}
  ],
  "methodological_note": ""
}}

DADOS:

{json.dumps(records, ensure_ascii=False)}
"""

        raw = call_model(
            client,
            model,
            prompt
        )

        parsed = safe_json(raw)

        thematic_rows.append(
            {
                "question_id": qid,
                "model": model,
                "prompt_version": PROMPT_VERSION,
                "run_date": timestamp,
                "raw_response": raw,
                "parsed_json": json.dumps(
                    parsed,
                    ensure_ascii=False
                ),
            }
        )

        print(
            f"{qid}: concluída"
        )

    thematic = pd.DataFrame(
        thematic_rows
    )

    thematic_file = (
        out_dir
        / "q14_by_question.csv"
    )

    thematic.to_csv(
        thematic_file,
        index=False,
        encoding="utf-8-sig"
    )

    payload = []

    for _, row in thematic.iterrows():

        parsed = safe_json(
            row["raw_response"]
        )

        if parsed:
            payload.append(parsed)
        else:
            payload.append(
                {
                    "question_id":
                        row["question_id"],
                    "raw_response":
                        row["raw_response"]
                }
            )

    final_prompt = f"""
Produza a síntese final da Q14 usando SOMENTE
as 13 comparações temáticas fornecidas.

Pergunta Q14:

Quais convergências, diferenças, lacunas de evidência
e padrões recorrentes podem ser identificados entre
os países a partir das evidências previamente recuperadas
e validadas?

REGRAS:

- Não faça ranking.
- Não utilize conhecimento externo.
- Não volte ao corpus bruto.
- Não transforme inconclusive em ausência conceitual.
- Não invente países ou padrões.
- Toda síntese deve ser rastreável às perguntas Q01-Q13.
- Responda SOMENTE em JSON válido.

Formato obrigatório:

{{
  "question_id": "Q14",
  "synthesis": "",
  "major_convergences": [
    {{
      "claim": "",
      "countries": [],
      "source_questions": []
    }}
  ],
  "major_differences": [
    {{
      "claim": "",
      "countries": [],
      "source_questions": []
    }}
  ],
  "recurring_patterns": [
    {{
      "claim": "",
      "countries": [],
      "source_questions": []
    }}
  ],
  "evidence_gaps": [
    {{
      "claim": "",
      "countries": [],
      "source_questions": []
    }}
  ],
  "limitations": []
}}

COMPARAÇÕES TEMÁTICAS:

{json.dumps(payload, ensure_ascii=False)}
"""

    final_raw = call_model(
        client,
        model,
        final_prompt
    )

    final_parsed = safe_json(
        final_raw
    )

    final_file = (
        out_dir
        / "q14_final.json"
    )

    final_file.write_text(
        json.dumps(
            {
                "question_id": "Q14",
                "model": model,
                "prompt_version":
                    PROMPT_VERSION,
                "run_date": timestamp,
                "result": final_parsed,
                "raw_response":
                    final_raw,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print("Temáticas:", thematic_file)
    print("Síntese final:", final_file)


def main():

    load_dotenv(
        ROOT
        / "rag_project"
        / ".env"
    )

    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--input",
        default=str(DEFAULT_INPUT)
    )

    ap.add_argument(
        "--out",
        default=str(DEFAULT_OUT)
    )

    ap.add_argument(
        "--model",
        default=DEFAULT_MODEL
    )

    args = ap.parse_args()

    run(
        Path(args.input),
        Path(args.out),
        args.model
    )


if __name__ == "__main__":
    main()
