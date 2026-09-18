from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_CSV = ROOT / "analysis" / "consolidado" / "evidencias_consolidadas.csv"
RESPONSES_CSV = ROOT / "analysis" / "consolidado" / "respostas_consolidadas.csv"
FRAMEWORK_CSV = ROOT / "rag_project" / "framework" / "unesco_dlgf_2018.csv"
OUTPUT_DIR = ROOT / "analysis" / "dlgf_2018"

MAPPING_CSV = OUTPUT_DIR / "dlgf_evidence_mapping.csv"
SUMMARY_CSV = OUTPUT_DIR / "dlgf_summary_country_area.csv"
MATRIX_CSV = OUTPUT_DIR / "dlgf_country_area_matrix.csv"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_framework() -> list[dict[str, str]]:
    rows = load_csv(FRAMEWORK_CSV)
    for row in rows:
        row["_keywords"] = [normalize(k) for k in row.get("keywords", "").split(";") if k.strip()]
        row["_name"] = normalize(row.get("competence_name", ""))
    return rows


def response_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row.get("country", ""), row.get("question_id", ""))
        out[key] = row.get("response", "")
    return out


def classify(text: str, framework: list[dict[str, str]]) -> list[dict[str, str]]:
    ntext = normalize(text)
    if not ntext:
        return []

    candidates: list[dict[str, str]] = []
    for item in framework:
        matched = sorted({kw for kw in item["_keywords"] if kw and kw in ntext})
        exact_name = bool(item["_name"] and item["_name"] in ntext)
        if exact_name or matched:
            hit_count = len(matched) + (2 if exact_name else 0)
            if exact_name or hit_count >= 2:
                correspondence = "strong"
            elif hit_count == 1:
                correspondence = "candidate"
            else:
                correspondence = "inconclusive"
            candidates.append({
                "area_code": item["area_code"],
                "area_name": item["area_name"],
                "competence_code": item["competence_code"],
                "competence_name": item["competence_name"],
                "correspondence": correspondence,
                "matched_terms": " | ".join(matched),
                "match_count": str(hit_count),
            })
    return candidates


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence = load_csv(EVIDENCE_CSV)
    responses = load_csv(RESPONSES_CSV)
    framework = load_framework()
    responses_by_key = response_lookup(responses)

    output_rows: list[dict[str, str]] = []
    for row in evidence:
        country = row.get("country", "")
        question_id = row.get("question_id", "")
        evidence_number = row.get("evidence_number", "")
        original_text = row.get("original_text", "")
        fallback_response = responses_by_key.get((country, question_id), "")
        text = original_text.strip() or fallback_response.strip()
        source_layer = "evidence_original_text" if original_text.strip() else (
            "response_fallback" if fallback_response.strip() else "no_text"
        )

        evidence_id = row.get("evidence_id", "").strip()
        evidence_id_origin = "preserved"
        if not evidence_id:
            evidence_id = f"{country}:{question_id}:E{evidence_number or 'NA'}"
            evidence_id_origin = "derived_from_country_question_evidence_number"

        matches = classify(text, framework)
        if not matches:
            matches = [{
                "area_code": "",
                "area_name": "",
                "competence_code": "",
                "competence_name": "",
                "correspondence": "not_detected",
                "matched_terms": "",
                "match_count": "0",
            }]

        for match in matches:
            output_rows.append({
                "country": country,
                "question_id": question_id,
                "evidence_id": evidence_id,
                "evidence_id_origin": evidence_id_origin,
                "document_id": row.get("document_id", ""),
                "document": row.get("document", ""),
                "page": row.get("page", ""),
                "original_text": original_text,
                "classification_original": row.get("classification", ""),
                "validation_status_original": row.get("evidence_validation_status", ""),
                "source_layer": source_layer,
                "dlgf_area_code": match["area_code"],
                "dlgf_area_name": match["area_name"],
                "dlgf_competence_code": match["competence_code"],
                "dlgf_competence_name": match["competence_name"],
                "correspondence": match["correspondence"],
                "matched_terms": match["matched_terms"],
                "match_count": match["match_count"],
                "framework_id": "UNESCO_DLGF_2018",
                "analytical_note": (
                    "Classificação auxiliar por baixa inferência lexical. "
                    "Requer validação humana antes de interpretação substantiva."
                ),
            })

    fieldnames = list(output_rows[0].keys()) if output_rows else []
    with MAPPING_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    summary: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    countries: set[str] = set()
    areas: dict[str, str] = {}
    for row in output_rows:
        country = row["country"]
        countries.add(country)
        area_code = row["dlgf_area_code"]
        area_name = row["dlgf_area_name"]
        if area_code and row["correspondence"] in {"strong", "candidate"}:
            areas[area_code] = area_name
            summary[(country, area_code, area_name)].add(row["evidence_id"])

    summary_rows = [
        {
            "country": country,
            "dlgf_area_code": area_code,
            "dlgf_area_name": area_name,
            "evidence_count": len(ids),
            "interpretation_limit": "Contagem de evidências classificadas; não representa qualidade, desempenho ou implementação curricular.",
        }
        for (country, area_code, area_name), ids in sorted(summary.items())
    ]

    with SUMMARY_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["country", "dlgf_area_code", "dlgf_area_name", "evidence_count", "interpretation_limit"],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    ordered_areas = sorted(areas, key=lambda value: float(value))
    with MATRIX_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = ["country"] + [f"CA{code}_{areas[code]}" for code in ordered_areas]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for country in sorted(countries):
            record = {"country": country}
            for code in ordered_areas:
                record[f"CA{code}_{areas[code]}"] = len(summary.get((country, code, areas[code]), set()))
            writer.writerow(record)

    try:
        import matplotlib.pyplot as plt
        import pandas as pd

        matrix = pd.read_csv(MATRIX_CSV)
        if not matrix.empty and len(matrix.columns) > 1:
            values = matrix.set_index("country")
            fig, ax = plt.subplots(figsize=(12, max(6, len(values) * 0.35)))
            image = ax.imshow(values.values, aspect="auto")
            ax.set_xticks(range(len(values.columns)))
            ax.set_xticklabels(values.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(values.index)))
            ax.set_yticklabels(values.index)
            ax.set_title("Evidências documentais classificadas por dimensão UNESCO/UIS DLGF 2018")
            ax.set_xlabel("Áreas do DLGF")
            ax.set_ylabel("País")
            fig.colorbar(image, ax=ax, label="Número de evidências classificadas")
            fig.text(
                0.5,
                0.01,
                "Leitura descritiva: a contagem não representa qualidade curricular, desempenho ou grau de implementação.",
                ha="center",
                fontsize=8,
            )
            fig.tight_layout(rect=(0, 0.04, 1, 1))
            fig.savefig(OUTPUT_DIR / "dlgf_country_area_matrix.png", dpi=200)
            plt.close(fig)
    except ImportError:
        pass

    print(f"Mapeamento: {MAPPING_CSV}")
    print(f"Resumo: {SUMMARY_CSV}")
    print(f"Matriz: {MATRIX_CSV}")


if __name__ == "__main__":
    main()
