from pathlib import Path
import pandas as pd
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]

BASE = (
    ROOT
    / "analysis"
    / "official_run_20260912"
    / "comparison"
)

VALID_COUNTRIES = [
    "africa-do-sul",
    "australia",
    "brasil",
    "canada",
    "chile",
    "china",
    "coreia-do-sul",
    "estonia",
    "eua",
    "finlandia",
    "gana",
    "hong-kong",
    "irlanda",
    "japao",
    "nova-zelandia",
    "quenia",outfile = BASE / "q14_final_v3.json"outfile = BASE / "q14_final_v3.json"
    "reino-unido",
    "ruanda",
    "singapura",
    "suica",
    "taiwan",
    "uruguai",
]

VALID_QUESTIONS = [f"Q{i:02d}" for i in range(1, 14)]


def parse_json(text):
    text = str(text).strip()

    if text.startswith("```"):
        text = (
            text.replace("```json", "", 1)
            .replace("```", "")
            .strip()
        )

    return json.loads(text)


def main():

    load_dotenv(ROOT / "rag_project" / ".env")

    thematic = pd.read_csv(
        BASE / "q14_by_question.csv"
    )

    payload = []

    for _, row in thematic.iterrows():

        try:
            obj = json.loads(row["parsed_json"])
        except Exception:
            obj = parse_json(row["raw_response"])

        payload.append(obj)

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )

    prompt = f"""
Você realizará SOMENTE a síntese comparativa final Q14
de uma pesquisa documental internacional sobre
Computação e Educação Digital.

Use exclusivamente as 13 comparações temáticas fornecidas.

PAÍSES VÁLIDOS:
{json.dumps(VALID_COUNTRIES, ensure_ascii=False)}

PERGUNTAS-FONTE VÁLIDAS:
{json.dumps(VALID_QUESTIONS, ensure_ascii=False)}

REGRAS METODOLÓGICAS OBRIGATÓRIAS:

1. Não use conhecimento externo.
2. Não consulte novamente o corpus.
3. Não invente países.
4. Use somente os identificadores de países da lista fornecida.
5. Não crie variantes como "kenia" para "quenia".
6. Não faça ranking de países.
7. Não use expressões como:
   - melhor;
   - pior;
   - mais avançado;
   - maior alinhamento;
   - mais focado;
   - menos focado;
   - mais prático;
   - menos prático.
8. Não faça afirmações sobre:
   - efetividade;
   - impacto;
   - sucesso;
   - implementação observada;
   - aplicação real em sala de aula;
   pois o corpus é documental e não mede esses fenômenos.
9. "inconclusive" significa somente insuficiência
   de evidência recuperada.
10. Nunca transforme "inconclusive" em ausência
    do conceito no currículo do país.
11. Diferencie rigorosamente:
    - convergência documental;
    - diferença de formulação/ênfase documental;
    - padrão recorrente;
    - lacuna de evidência recuperada.
12. Uma lacuna de evidência NÃO significa que o país
    não possui o conceito.
13. Cada afirmação deve mencionar somente países
    efetivamente sustentados pelas comparações fornecidas.
14. Cada item deve indicar perguntas-fonte compatíveis
    com o conteúdo da afirmação.
15. Q11 trata de CIDADANIA GLOBAL.
    Não utilize Q11 isoladamente para sustentar afirmações
    sobre cidadania digital.
16. Q12 trata de FORMAÇÃO E DESENVOLVIMENTO DOCENTE.
    Afirmações especificamente sobre formação docente
    devem incluir Q12 como fonte.
17. Não introduza categorias analíticas novas.
18. As limitações são obrigatórias e devem incluir
    pelo menos:
    - heterogeneidade documental entre países;
    - quantidade desigual de documentos;
    - resultados inconclusive;
    - ausência de recuperação não equivale a ausência conceitual;
    - mediação por tradução e recuperação semântica;
    - análise documental não mede implementação ou impacto.

RESPONDA SOMENTE EM JSON VÁLIDO:

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

    response = client.responses.create(
        model=os.environ.get(
            "OPENAI_Q14_MODEL",
            "gpt-4o-mini"
        ),
        input=prompt
    )

    raw = response.output_text
    result = parse_json(raw)

    output = {
        "question_id": "Q14",
        "prompt_version": "q14-comparison-v1.1-strict",
        "result": result,
        "raw_response": raw,
    }

    outfile = BASE / "q14_final_v3.json"

    outfile.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("Arquivo:", outfile)
    print("\nSÍNTESE:")
    print(result.get("synthesis", ""))

    print("\nConvergências:",
          len(result.get("major_convergences", [])))
    print("Diferenças:",
          len(result.get("major_differences", [])))
    print("Padrões:",
          len(result.get("recurring_patterns", [])))
    print("Lacunas:",
          len(result.get("evidence_gaps", [])))
    print("Limitações:",
          len(result.get("limitations", [])))


if __name__ == "__main__":
    main()