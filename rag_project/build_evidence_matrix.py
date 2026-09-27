from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from rag_project.paths import ANALYSIS_DIR

ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK_CSV = ROOT / "rag_project" / "framework" / "unesco_dlgf_2018.csv"
VALIDATED_STATUSES = {"validated", "validado", "reformulated", "reformulado"}
AREA_COLUMNS = [str(code) for code in range(7)]


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
    for evidence in evidence_rows:
        validation_status = str(evidence.get("validation_status", "")).strip().lower()
        if validation_status not in VALIDATED_STATUSES:
            continue
        text = evidence.get("source_text") or evidence.get("evidence_text") or evidence.get("original_text") or ""
        matches = detect_framework_hits(text, framework)
        if not matches:
            matches = [{
                "framework_id": "DLGF_2018",
                "dimension_code": "",
                "dimension_name": "",
                "keyword": "",
                "match_type": "not_detected",
            }]
        for hit in matches:
            matrix_rows.append({
                "evidence_id": evidence.get("evidence_id", ""),
                "question_id": evidence.get("question_id", ""),
                "country": evidence.get("country", ""),
                "document_id": evidence.get("document_id", ""),
                "document_title": evidence.get("document_title", ""),
                "page_start": evidence.get("page_start", evidence.get("page", "")),
                "page_end": evidence.get("page_end", evidence.get("page", "")),
                "source_text": text,
                "validation_status": validation_status,
                "framework_id": "DLGF_2018",
                "area_code": hit["dimension_code"],
                "area_name": hit["dimension_name"],
                "matched_terms": hit["keyword"],
                "correspondence": hit["match_type"],
                "review_note": "Correspondência auxiliar; interpretar somente após conferência humana na fonte original.",
            })

    mapping_fields = [
        "evidence_id", "question_id", "country", "document_id", "document_title",
        "page_start", "page_end", "source_text", "validation_status", "framework_id",
        "area_code", "area_name", "matched_terms", "correspondence", "review_note",
    ]
    _write_csv(out_dir / "evidence_matrix.csv", matrix_rows, mapping_fields)

    evidence_by_country_area: dict[tuple[str, str], set[str]] = defaultdict(set)
    countries = sorted({row["country"] for row in matrix_rows if row["country"]})
    for row in matrix_rows:
        if row["area_code"] and row["correspondence"] in {"strong", "candidate"} and row["evidence_id"]:
            evidence_by_country_area[(row["country"], row["area_code"])].add(row["evidence_id"])

    summary = [
        {"country": country, "area_code": area["code"], "area_name": area["name"],
         "validated_evidence_count": len(evidence_by_country_area[(country, area["code"])]),
         "interpretation_limit": "Contagem descritiva; não representa qualidade nem implementação curricular."}
        for country in countries
        for area in framework
    ]
    _write_csv(
        out_dir / "dlgf_summary_country_area.csv",
        summary,
        ["country", "area_code", "area_name", "validated_evidence_count", "interpretation_limit"],
    )

    matrix = [
        {"country": country, **{f"area_{code}": len(evidence_by_country_area[(country, code)]) for code in AREA_COLUMNS}}
        for country in countries
    ]
    _write_csv(out_dir / "dlgf_country_area_matrix.csv", matrix, ["country"] + [f"area_{code}" for code in AREA_COLUMNS])
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
