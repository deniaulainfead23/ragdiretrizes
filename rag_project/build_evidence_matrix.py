from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from rag_project.corpus_registry import EXCLUDED_COUNTRIES, load_registry
from rag_project.paths import ANALYSIS_DIR

ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_CSV = ROOT / "rag_project" / "framework" / "unesco_dlgf_2018.csv"
VALIDATED_STATUSES = {
    "validated", "validado", "validada", "reformulated", "reformulado", "reformulada",
    "confirmado", "confirmada", "confirmed",
}
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower()
    value = re.sub(r"[^a-z0-9.]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_framework(path: Path = FRAMEWORK_CSV) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["_keywords"] = [normalize(term) for term in row.get("keywords", "").split(";") if term.strip()]
        row["_name"] = normalize(row.get("name", ""))
    return rows


def detect_framework_hits(text: str, framework: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    normalized = normalize(text)
    if not normalized:
        return []
    framework = framework or load_framework()
    hits = []
    for area in framework:
        matched = sorted({term for term in area["_keywords"] if term and term in normalized})
        exact_name = bool(area["_name"] and area["_name"] in normalized)
        if not matched and not exact_name:
            continue
        score = len(matched) + (2 if exact_name else 0)
        hits.append({
            "framework_id": "DLGF_2018",
            "dimension_code": area["code"],
            "dimension_name": area["name"],
            "keyword": " | ".join(matched) or area["_name"],
            "match_type": "strong" if exact_name or score >= 2 else "candidate",
        })
    return hits


def classify_evidence_record(snippet: str, framework_id: str = "DLGF_2018", dimension_code: str = "", dimension_name: str = "", api_key: str | None = None, model: str = "") -> dict[str, str]:
    if framework_id != "DLGF_2018":
        raise ValueError("Somente DLGF_2018 está ativo como framework internacional")
    hits = detect_framework_hits(snippet)
    selected = next((hit for hit in hits if not dimension_code or hit["dimension_code"] == dimension_code), None)
    if selected is None:
        return {
            "evidence_classification": "none",
            "evidence_status": "candidate",
            "validation_notes": "Nenhuma correspondência lexical detectada; validar manualmente antes de concluir.",
        }
    return {
        "evidence_classification": "explicit" if selected["match_type"] == "strong" else "implicit",
        "evidence_status": "candidate",
        "validation_notes": "Classificação automática preliminar DLGF; exige validação humana.",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_evidence_matrix(evidence_csv: str | Path, output_dir: str | Path) -> list[dict[str, Any]]:
    source_path = Path(evidence_csv)
    out_dir = Path(output_dir)
    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        evidence_rows = list(csv.DictReader(handle))

    framework = load_framework()
    matrix_rows: list[dict[str, Any]] = []
    assessable_by_country: dict[str, bool] = defaultdict(bool)
    translation_needed_by_country: dict[str, bool] = defaultdict(bool)
    source_text_missing_by_country: dict[str, bool] = defaultdict(bool)
    evidence_by_country_area: dict[tuple[str, str], set[str]] = defaultdict(set)
    for evidence in evidence_rows:
        validation_status = str(
            evidence.get("validation_status")
            or evidence.get("evidence_validation_status")
            or evidence.get("validation_status_original")
            or ""
        ).strip().lower()
        if validation_status not in VALIDATED_STATUSES:
            continue
        country = str(evidence.get("country", "")).strip().lower()
        if not country:
            continue
        translated_text = str(
            evidence.get("translated_text_en") or evidence.get("translated_text_pt") or evidence.get("translated_text") or ""
        ).strip()
        text = translated_text or str(
            evidence.get("source_text") or evidence.get("evidence_text") or evidence.get("original_text") or ""
        )
        needs_translation = bool(CJK_RE.search(text)) and not translated_text
        if needs_translation:
            translation_needed_by_country[country] = True
        elif normalize(text):
            assessable_by_country[country] = True
        else:
            source_text_missing_by_country[country] = True
        matches = detect_framework_hits(text, framework)
        if not matches:
            matches = [{
                "framework_id": "DLGF_2018",
                "dimension_code": "",
                "dimension_name": "",
                "keyword": "",
                "match_type": "translation_required" if needs_translation else "not_detected",
            }]
        evidence_id = str(evidence.get("evidence_id", "")).strip() or ":".join(filter(None, [
            country, str(evidence.get("question_id", "")).strip(),
            str(evidence.get("document_id", "")).strip(),
            str(evidence.get("page_start") or evidence.get("page", "")).strip(),
        ]))
        for hit in matches:
            area_code = hit["dimension_code"]
            if area_code and hit["match_type"] in {"strong", "candidate"}:
                evidence_by_country_area[(country, area_code)].add(evidence_id)
            matrix_rows.append({
                "evidence_id": evidence_id,
                "question_id": evidence.get("question_id", ""),
                "country": country,
                "document_id": evidence.get("document_id", ""),
                "document_title": evidence.get("document_title") or evidence.get("document", ""),
                "page_start": evidence.get("page_start") or evidence.get("page", ""),
                "page_end": evidence.get("page_end") or evidence.get("page", ""),
                "source_text": text,
                "validation_status": validation_status,
                "source_language": evidence.get("source_language", ""),
                "translation_status": evidence.get("translation_status", ""),
                "framework_id": "DLGF_2018",
                "area_code": area_code,
                "area_name": hit["dimension_name"],
                "matched_terms": hit["keyword"],
                "correspondence": hit["match_type"],
                "review_note": (
                    "Trecho em japonês/chinês sem tradução disponível; não avaliado lexicalmente."
                    if hit["match_type"] == "translation_required" else
                    "Correspondência lexical auxiliar; confirmar tradução e sentido na fonte oficial."
                ),
            })

    mapping_fields = [
        "evidence_id", "question_id", "country", "document_id", "document_title",
        "page_start", "page_end", "source_text", "validation_status", "source_language", "translation_status", "framework_id",
        "area_code", "area_name", "matched_terms", "correspondence", "review_note",
    ]
    _write_csv(out_dir / "evidence_matrix.csv", matrix_rows, mapping_fields)

    registry = load_registry()
    countries = {
        str(entry.get("country", "")).strip().lower()
        for entry in registry.get("countries", [])
        if entry.get("include_in_analysis") and str(entry.get("country", "")).lower() not in EXCLUDED_COUNTRIES
    }
    countries.update(row["country"] for row in matrix_rows if row["country"])
    countries = sorted(countries)
    countries_with_validated_rows = {row["country"] for row in matrix_rows}
    country_state: dict[str, str] = {}
    summary = []
    for country in countries:
        if country not in countries_with_validated_rows:
            state = "no_validated_evidence"
        elif translation_needed_by_country[country] or not assessable_by_country[country]:
            state = "translation_required" if translation_needed_by_country[country] else "no_assessable_text"
        else:
            state = "reviewed_sample"
        country_state[country] = state
        for area in framework:
            count = len(evidence_by_country_area[(country, area["code"])])
            area_status = (
                "not_assessed" if state in {"no_validated_evidence", "no_assessable_text"}
                else "evidence_mapped" if count
                else "translation_required" if state == "translation_required"
                else "no_match_in_reviewed_sample"
            )
            summary.append({
                "country": country,
                "framework_id": "DLGF_2018",
                "area_code": area["code"],
                "area_name": area["name"],
                "evidence_count": count if area_status != "not_assessed" else "",
                "assessment_status": area_status,
                "interpretation_limit": "Contagem no conjunto de evidências revisado; não mede currículo completo nem ausência conceitual.",
            })
    _write_csv(
        out_dir / "dlgf_summary_country_area.csv",
        summary,
        ["country", "framework_id", "area_code", "area_name", "evidence_count", "assessment_status", "interpretation_limit"],
    )

    area_columns = [f"CA{area['code']}_{area['name']}" for area in framework]
    matrix = []
    for country in countries:
        row: dict[str, Any] = {"country": country, "assessment_status": country_state[country]}
        for area, column in zip(framework, area_columns):
            count = len(evidence_by_country_area[(country, area["code"])])
            row[column] = count if count else (
                "not_assessed" if country_state[country] in {"no_validated_evidence", "no_assessable_text"}
                else "translation_required" if country_state[country] == "translation_required"
                else "no_match_in_reviewed_sample"
            )
        matrix.append(row)
    _write_csv(out_dir / "dlgf_country_area_matrix.csv", matrix, ["country", "assessment_status"] + area_columns)
    return matrix_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Classifica evidências RAG validadas pelas sete áreas do DLGF 2018.")
    parser.add_argument("--evidence", required=True, help="CSV de evidências nacionais da rodada")
    parser.add_argument("--out", type=Path, default=ANALYSIS_DIR / "dlgf_2018", help="Pasta de saída da matriz")
    args = parser.parse_args()
    rows = build_evidence_matrix(args.evidence, args.out)
    print(f"Evidências validadas classificadas: {len(rows)}")
    print(f"Matriz: {args.out / 'evidence_matrix.csv'}")


if __name__ == "__main__":
    main()
