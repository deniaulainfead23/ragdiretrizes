"""Prepara um pacote público e reprodutível para depósito no Zenodo.

O script NÃO altera o corpus original e NÃO redistribui PDFs de terceiros.
Ele reúne metadados, resultados derivados e evidências que passam por filtros
mínimos de qualidade. A revisão humana final continua obrigatória.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "zenodo_package"
META = ROOT / "metadata" / "bibliographic_matrix.csv"
MANIFEST = ROOT / "corpus" / "MANIFESTO.md"
EVIDENCE = ROOT / "analysis" / "evidence" / "evidence_matrix.csv"
LEXICAL = ROOT / "corpus" / "analysis_output"
MODEL_XLSX = ROOT / "corpus" / "datasetModelo" / "dataset_comparativo_curriculos.xlsx"

LEXICAL_FILES = [
    "lexical_document_tfidf.csv",
    "lexical_document_top_terms.csv",
    "lexical_group_tfidf.csv",
    "lexical_group_frequency.csv",
    "lexical_group_similarity.csv",
    "lexical_group_similarity_matrix.csv",
    "lexical_country_similarity_ranking.csv",
    "country_unesco_reference.csv",
    "analysis_summary.json",
]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        if fieldnames:
            with path.open("w", encoding="utf-8", newline="") as handle:
                csv.DictWriter(handle, fieldnames=fieldnames).writeheader()
        return
    fieldnames = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_filename(value: str) -> str:
    name = Path(value or "").name.lower()
    name = re.sub(r"_(falha_download|indisponivel)\.txt$", ".pdf", name)
    name = re.sub(r"[^a-z0-9]+", "", name)
    return name


def parse_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    rows: list[dict] = []
    for line in MANIFEST.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith("|") or "`" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5 or cells[0].lower() in {"país", "---"}:
            continue
        country, file_cell, status, size, source = cells[:5]
        file_match = re.search(r"`([^`]+)`", file_cell)
        url_match = re.search(r"https?://[^\s—]+", source)
        rows.append({
            "country_manifest": country,
            "manifest_file": file_match.group(1) if file_match else file_cell,
            "source_status": status,
            "manifest_size": re.sub(r"\D", "", size),
            "official_url_manifest": url_match.group(0).rstrip(".,;)") if url_match else "",
            "manifest_note": source,
        })
    return rows


def reconcile_sources(biblio: list[dict], manifest: list[dict]) -> tuple[list[dict], list[dict]]:
    manifest_index = {normalize_filename(r["manifest_file"]): r for r in manifest}
    registry: list[dict] = []
    enriched: list[dict] = []

    for row in biblio:
        new = dict(row)
        key = normalize_filename(row.get("file_name") or row.get("relative_path") or "")
        match = manifest_index.get(key)
        if not match:
            # fallback por similaridade de nome simplificada
            candidates = [m for k, m in manifest_index.items() if key and (key in k or k in key)]
            match = candidates[0] if len(candidates) == 1 else None

        official_url = (row.get("official_source_url") or "").strip()
        source_status = ""
        manifest_note = ""
        if match:
            official_url = official_url or match.get("official_url_manifest", "")
            source_status = match.get("source_status", "")
            manifest_note = match.get("manifest_note", "")

        if official_url and not new.get("official_source_url"):
            new["official_source_url"] = official_url
        enriched.append(new)

        citation_abnt = make_abnt(new, official_url)
        citation_apa = make_apa(new, official_url)
        registry.append({
            "document_id": row.get("document_id", ""),
            "country": row.get("country", ""),
            "title": row.get("title_original", ""),
            "institution": row.get("institution", ""),
            "year": row.get("publication_year_original", "") or row.get("publication_year_version_used", ""),
            "official_url": official_url,
            "access_date": row.get("access_date", ""),
            "sha256": row.get("sha256", ""),
            "source_status": source_status,
            "redistribution_status": "metadata_only",
            "license_original": "",
            "license_verification_status": "needs_review",
            "citation_abnt": citation_abnt,
            "citation_apa7": citation_apa,
            "notes": manifest_note,
        })
    return enriched, registry


def make_abnt(row: dict, url: str) -> str:
    institution = (row.get("institution") or "").strip()
    title = (row.get("title_original") or "").strip()
    year = (row.get("publication_year_original") or row.get("publication_year_version_used") or "").strip()
    access = (row.get("access_date") or "").strip()
    if not institution or not title:
        return ""
    parts = [f"{institution.upper()}. {title}."]
    if year:
        parts.append(f" {year}.")
    if url:
        parts.append(f" Disponível em: {url}.")
    if access:
        parts.append(f" Acesso em: {access}.")
    return "".join(parts)


def make_apa(row: dict, url: str) -> str:
    institution = (row.get("institution") or "").strip()
    title = (row.get("title_original") or "").strip()
    year = (row.get("publication_year_original") or row.get("publication_year_version_used") or "n.d.").strip()
    if not institution or not title:
        return ""
    suffix = f" {url}" if url else ""
    return f"{institution}. ({year}). {title}.{suffix}".strip()


def looks_like_pdf_binary(text: str) -> bool:
    sample = (text or "")[:1000]
    markers = ["%PDF-", " obj ", "/Type/", "stream", "/FlateDecode", "endobj"]
    return sum(marker in sample for marker in markers) >= 2


def evidence_outputs(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    candidates: list[dict] = []
    validated: list[dict] = []
    for row in rows:
        text = (row.get("matched_text") or "").strip()
        notes = (row.get("validation_notes") or "").lower()
        status = (row.get("evidence_status") or "").lower()
        clean_text = bool(text) and not looks_like_pdf_binary(text)
        requires_human = "human validation" in notes or "fallback" in notes

        candidate = dict(row)
        candidate["publication_filter_text_clean"] = str(clean_text).lower()
        candidate["publication_filter_human_review_required"] = str(requires_human).lower()
        candidates.append(candidate)

        if clean_text and status == "validated" and not requires_human:
            validated.append(row)
    return candidates, validated


def copy_if_exists(source: Path, target: Path) -> None:
    if source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def create_package_readme(registry: list[dict], validated_count: int, candidate_count: int) -> None:
    n_sources = len(registry)
    n_urls = sum(bool(r.get("official_url")) for r in registry)
    text = f"""# Comparative Dataset of Computing, Digital Education and Digital Citizenship Curricula in Basic Education

Version 1.0.0 — pre-publication package.

## Contents

This package contains research-derived metadata, lexical indicators and documentary evidence supporting a comparative study of Computing, Digital Education, Computational Thinking and Digital Citizenship in Basic Education.

- Bibliographic records: {n_sources}
- Records with an official URL currently reconciled: {n_urls}
- Evidence records inspected by publication filters: {candidate_count}
- Evidence records automatically eligible for the validated public file: {validated_count}

## Important methodological note

TF-IDF and cosine similarity are exploratory lexical indicators. They must not be interpreted as direct measures of curriculum quality, curricular equivalence or substantive alignment.

## Third-party documents

Original curriculum PDFs are not included in this public package by default. Their official URLs and checksums are provided when available. Redistribution of third-party documents requires separate license verification.

## Evidence validation

`evidence_matrix_candidate_for_validation.csv` is an audit file. `evidence_matrix_validated.csv` contains only records that passed the automated publication filters. Human review is still required before the Zenodo release.

## License

Original research data and derived outputs: CC BY 4.0, unless otherwise indicated. Third-party materials retain their original rights.

## Citation

See `CITATION.cff`. Add the reserved Zenodo DOI before final publication.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    biblio = read_csv(META)
    manifest = parse_manifest()
    enriched_biblio, registry = reconcile_sources(biblio, manifest)

    write_csv(OUT / "metadata" / "bibliographic_matrix.csv", enriched_biblio)
    write_csv(OUT / "metadata" / "source_registry.csv", registry)
    write_csv(OUT / "metadata" / "document_checksums.csv", [
        {
            "document_id": r.get("document_id", ""),
            "country": r.get("country", ""),
            "file_name": r.get("file_name", ""),
            "sha256": r.get("sha256", ""),
            "file_size": r.get("file_size", ""),
        }
        for r in enriched_biblio if r.get("sha256")
    ])
    write_csv(OUT / "metadata" / "licensing_inventory.csv", [
        {
            "document_id": r.get("document_id", ""),
            "country": r.get("country", ""),
            "title": r.get("title", ""),
            "official_url": r.get("official_url", ""),
            "license_original": r.get("license_original", ""),
            "redistribution_status": r.get("redistribution_status", "metadata_only"),
            "license_verification_status": r.get("license_verification_status", "needs_review"),
        }
        for r in registry
    ])

    evidence = read_csv(EVIDENCE)
    candidates, validated = evidence_outputs(evidence)
    write_csv(OUT / "evidence" / "evidence_matrix_candidate_for_validation.csv", candidates)
    write_csv(OUT / "evidence" / "evidence_matrix_validated.csv", validated)

    for name in LEXICAL_FILES:
        copy_if_exists(LEXICAL / name, OUT / "lexical_analysis" / name)

    copy_if_exists(MODEL_XLSX, OUT / "comparative_dataset" / MODEL_XLSX.name)
    copy_if_exists(ROOT / "DOCUMENTACAO_METODOLOGICA.md", OUT / "methodology" / "methodology.md")
    copy_if_exists(ROOT / "corpus" / "MANIFESTO.md", OUT / "methodology" / "provenance.md")
    copy_if_exists(ROOT / "zenodo" / "CITATION.cff", OUT / "CITATION.cff")
    copy_if_exists(ROOT / "zenodo" / "LICENSE_DATA.txt", OUT / "LICENSE_DATA.txt")
    copy_if_exists(ROOT / "zenodo" / "data_dictionary.csv", OUT / "data_dictionary.csv")

    summary = {
        "package": str(OUT.relative_to(ROOT)),
        "bibliographic_records": len(enriched_biblio),
        "source_registry_records": len(registry),
        "sources_with_official_url": sum(bool(r.get("official_url")) for r in registry),
        "evidence_candidates": len(candidates),
        "evidence_validated_after_filters": len(validated),
        "human_review_required": True,
        "third_party_pdfs_included": False,
    }
    (OUT / "package_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    create_package_readme(registry, len(validated), len(candidates))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
