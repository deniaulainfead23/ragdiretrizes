#!/usr/bin/env python3
"""Additive, reproducible lexical screening of full curriculum documents.

Reads an existing JSONL dataset without modifying it, reunites page records by
document_id, searches a versioned DLGF competence codebook, and writes a new
run directory. Lexical matches are candidate indicators, not semantic or
curricular validation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

SCRIPT_VERSION = "0.1.0"
EXCLUDED_COUNTRIES = {"marrocos"}
WORD_RE = re.compile(r"(?u)\b[\w'-]+\b")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in value if not unicodedata.combining(char))


def compile_term(term: str) -> re.Pattern[str]:
    normalized = normalize(term).strip()
    escaped = re.escape(normalized).replace(r"\ ", r"\s+")
    return re.compile(r"(?<!\w)" + escaped + r"(?!\w)", re.UNICODE)


def read_jsonl(path: Path, text_field: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL inválido na linha {line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Registro JSONL não é objeto na linha {line_number}.")
            text = str(row.get(text_field) or "").strip()
            if not text:
                raise ValueError(
                    f"Campo {text_field!r} vazio/ausente na linha {line_number}. "
                    "Escolha explicitamente o campo de texto integral da base."
                )
            row["_analysis_text"] = text
            rows.append(row)
    if not rows:
        raise ValueError(f"Nenhum registro encontrado em {path}.")
    return rows


def load_codebook(path: Path) -> list[dict[str, str]]:
    required = {"framework_id", "area_code", "area_name", "competence_code",
                "competence_name", "description_en", "search_terms_en"}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"Codebook sem colunas obrigatórias: {missing}")
        rows = list(reader)
    codes = [row["competence_code"].strip() for row in rows]
    if not rows or len(codes) != len(set(codes)):
        raise ValueError("Codebook vazio ou com competence_code duplicado.")
    for row in rows:
        terms = [term.strip() for term in row["search_terms_en"].split("|") if term.strip()]
        if not terms:
            raise ValueError(f"Competência sem termos de busca: {row['competence_code']}")
        row["_compiled_terms"] = terms  # type: ignore[assignment]
    return rows


def document_key(row: dict[str, Any], ordinal: int) -> tuple[str, str]:
    scope = str(row.get("source_scope") or "").strip().casefold()
    framework = str(row.get("framework_source") or "").strip().casefold()
    group = str(row.get("dataset_group") or "").strip().casefold()
    if scope == "international_reference" or framework.startswith("dlgf") or group.startswith("unesco"):
        return "", ""
    country = str(row.get("country") or "").strip().casefold()
    doc_id = str(row.get("document_id") or row.get("document") or "").strip()
    if not country or not doc_id:
        raise ValueError(f"Registro {ordinal} sem country ou document_id/document.")
    if country in EXCLUDED_COUNTRIES:
        return "", ""
    return country, doc_id


def combine_documents(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for ordinal, row in enumerate(rows, start=1):
        country, doc_id = document_key(row, ordinal)
        if not country:
            continue
        key = (country, doc_id)
        if key not in grouped:
            grouped[key] = {
                "country": country,
                "document_id": doc_id,
                "document_title": str(row.get("document_title") or row.get("document") or doc_id),
                "source_path": str(row.get("source_path") or ""),
                "source_url": str(row.get("source_url") or ""),
                "year": str(row.get("year") or ""),
                "source_validation_status": str(row.get("validation_status") or ""),
                "translation_status": str(row.get("translation_status") or ""),
                "pages": [],
            }
        item = grouped[key]
        page = row.get("page_start", row.get("page", row.get("page_number", "")))
        item["pages"].append({"page": str(page), "text": row["_analysis_text"]})
        for field, source_field in (("source_path", "source_path"), ("source_url", "source_url"),
                                    ("year", "year"), ("source_validation_status", "validation_status"),
                                    ("translation_status", "translation_status")):
            value = str(row.get(source_field) or "").strip()
            if value and not item[field]:
                item[field] = value
    if not grouped:
        raise ValueError("Nenhum documento nacional elegível foi encontrado.")
    documents = []
    for item in grouped.values():
        item["pages"].sort(key=lambda part: (int(part["page"]) if part["page"].isdigit() else 10**12, part["page"]))
        item["text"] = "\n\n".join(part["text"] for part in item["pages"])
        item["word_count"] = len(WORD_RE.findall(item["text"]))
        documents.append(item)
    return sorted(documents, key=lambda item: (item["country"], item["document_id"]))


def count_term(text: str, term: str) -> int:
    return len(compile_term(term).findall(normalize(text)))


def find_term_matches(text: str, terms: list[str]) -> tuple[list[str], int]:
    """Return matched lexicon entries and unique, non-overlapping text spans.

    A phrase and one of its component terms can both match the same passage;
    counting merged spans avoids inflating the occurrence total in that case.
    """
    normalized_text = normalize(text)
    matched_terms: list[str] = []
    spans: list[tuple[int, int]] = []
    for term in terms:
        matches = list(compile_term(term).finditer(normalized_text))
        if matches:
            matched_terms.append(term)
            spans.extend(match.span() for match in matches)
    if not spans:
        return matched_terms, 0
    spans.sort()
    unique_spans: list[list[int]] = []
    for start, end in spans:
        if unique_spans and start < unique_spans[-1][1]:
            unique_spans[-1][1] = max(unique_spans[-1][1], end)
        else:
            unique_spans.append([start, end])
    return matched_terms, len(unique_spans)


def analyze(documents: list[dict[str, Any]], codebook: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    document_rows: list[dict[str, Any]] = []
    for doc in documents:
        for competence in codebook:
            terms = competence["_compiled_terms"]
            matched, total = find_term_matches(doc["text"], terms)
            matched_pages: set[str] = set()
            for page in doc["pages"]:
                _, page_hits = find_term_matches(page["text"], terms)
                if page_hits:
                    matched_pages.add(page["page"] or "not_recorded")
            words = int(doc["word_count"])
            document_rows.append({
                "country": doc["country"],
                "document_id": doc["document_id"],
                "document_title": doc["document_title"],
                "year": doc["year"],
                "source_path": doc["source_path"],
                "source_url": doc["source_url"],
                "source_validation_status": doc["source_validation_status"],
                "translation_status": doc["translation_status"],
                "framework_id": competence["framework_id"],
                "area_code": competence["area_code"],
                "area_name": competence["area_name"],
                "competence_code": competence["competence_code"],
                "competence_name": competence["competence_name"],
                "matched_terms": " | ".join(matched),
                "raw_occurrences": total,
                "document_words": words,
                "occurrences_per_10000_words": round(total * 10000 / words, 6) if words else 0,
                "lexical_hit": "yes" if total else "no",
                "hit_pages": " | ".join(sorted(matched_pages, key=lambda p: (not p.isdigit(), int(p) if p.isdigit() else p))),
            })

    by_country: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in document_rows:
        by_country[(row["country"], row["competence_code"])].append(row)
    country_rows: list[dict[str, Any]] = []
    for (country, code), rows in sorted(by_country.items()):
        hits = [row for row in rows if row["lexical_hit"] == "yes"]
        total_words = sum(int(row["document_words"]) for row in rows)
        total_occurrences = sum(int(row["raw_occurrences"]) for row in rows)
        competence = next(item for item in codebook if item["competence_code"] == code)
        country_rows.append({
            "country": country,
            "framework_id": competence["framework_id"],
            "area_code": competence["area_code"],
            "area_name": competence["area_name"],
            "competence_code": code,
            "competence_name": competence["competence_name"],
            "documents_in_country": len(rows),
            "documents_with_lexical_hit": len(hits),
            "document_coverage_percent": round(len(hits) * 100 / len(rows), 4) if rows else 0,
            "total_occurrences": total_occurrences,
            "total_words": total_words,
            "pooled_occurrences_per_10000_words": round(total_occurrences * 10000 / total_words, 6) if total_words else 0,
            "mean_document_rate_per_10000_words": round(mean(float(row["occurrences_per_10000_words"]) for row in rows), 6) if rows else 0,
            "interpretation": "lexical_indicator_only",
        })
    return document_rows, country_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_matrix(path: Path, country_rows: list[dict[str, Any]], codebook: list[dict[str, Any]]) -> None:
    codes = [row["competence_code"] for row in codebook]
    lookup = {(row["country"], row["competence_code"]): row for row in country_rows}
    countries = sorted({row["country"] for row in country_rows})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["country", "documents_in_country"] + codes)
        for country in countries:
            country_docs = max((int(row["documents_in_country"]) for row in country_rows if row["country"] == country), default=0)
            writer.writerow([country, country_docs] + [
                lookup[(country, code)]["document_coverage_percent"] if (country, code) in lookup else ""
                for code in codes
            ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSONL existente com um ou mais registros por documento.")
    parser.add_argument("--text-field", default="english_text", help="Campo textual a analisar; padrão: english_text.")
    parser.add_argument("--codebook", default=str(Path(__file__).with_name("unesco_dlgf_2018_competences.csv")))
    parser.add_argument("--out", required=True, help="Pasta nova e exclusiva da rodada; precisa não existir.")
    parser.add_argument("--run-id", required=True, help="Identificador reproduzível da rodada.")
    parser.add_argument("--source-revision", default="", help="Commit Git/ref exato do projeto que gerou os dados.")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    codebook_path = Path(args.codebook).resolve()
    output_dir = Path(args.out).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Dataset não encontrado: {input_path}")
    if not codebook_path.is_file():
        raise FileNotFoundError(f"Codebook não encontrado: {codebook_path}")
    if output_dir.exists():
        raise FileExistsError(f"A pasta de saída já existe; use uma nova: {output_dir}")
    output_dir.mkdir(parents=True)

    raw_rows = read_jsonl(input_path, args.text_field)
    docs = combine_documents(raw_rows)
    codebook = load_codebook(codebook_path)
    doc_rows, country_rows = analyze(docs, codebook)

    doc_fields = list(doc_rows[0])
    country_fields = list(country_rows[0])
    write_csv(output_dir / "document_competence_hits.csv", doc_rows, doc_fields)
    write_csv(output_dir / "country_competence_summary.csv", country_rows, country_fields)
    write_matrix(output_dir / "country_competence_matrix.csv", country_rows, codebook)

    manifest = {
        "analysis_name": "DLGF 2018 lexical competence screening",
        "script_version": SCRIPT_VERSION,
        "run_id": args.run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": args.source_revision,
        "inputs": {
            "dataset": {"path": str(input_path), "sha256": sha256_file(input_path), "text_field": args.text_field},
            "codebook": {"path": str(codebook_path), "sha256": sha256_file(codebook_path)},
        },
        "software": {"python": platform.python_version(), "platform": platform.platform()},
        "parameters": {"normalization": "casefold plus Unicode accent removal", "matching": "whole-word and whole-phrase exact lexical search", "unit_of_analysis": "full document; page rows reunited by document_id", "aggregation": "country x competence; coverage plus raw and length-normalized frequency", "excluded_countries": sorted(EXCLUDED_COUNTRIES)},
        "counts": {"input_records": len(raw_rows), "documents": len(docs), "countries": len({doc["country"] for doc in docs}), "competences": len(codebook), "document_competence_rows": len(doc_rows)},
        "interpretive_limit": "Lexical matches are search indicators, not evidence of semantic or curricular equivalence. Zero matches do not prove conceptual absence.",
        "outputs": {},
    }
    for name in ("document_competence_hits.csv", "country_competence_summary.csv", "country_competence_matrix.csv"):
        target = output_dir / name
        manifest["outputs"][name] = {"sha256": sha256_file(target), "bytes": target.stat().st_size}
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Documentos: {len(docs)} | países: {manifest['counts']['countries']} | competências: {len(codebook)}")
    print(f"Resultados: {output_dir}")
    print("Busca lexical concluída. Interprete ocorrências como indicadores, não como validação curricular automática.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(2)
