from pathlib import Path
import re
import unicodedata
import csv
import pandas as pd
import pdfplumber

from rag_project.corpus_registry import load_registry
from rag_project.paths import CORPUS_DIR, METADATA_DIR

CORPUS = CORPUS_DIR
AUDIT = METADATA_DIR / "auditoria" / "auditoria_corpus_classificacao_ABCD.csv"
OUTPUT = METADATA_DIR / "documentos.csv"
SOURCE_MANIFEST = METADATA_DIR / "corpus_manifest.csv"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.replace("\\", "/").strip().lower()


def load_audit():
    df = pd.read_csv(AUDIT)
    result = {}
    for row in df.to_dict("records"):
        rel = str(row["arquivo"]).replace("\\", "/").split("/corpus/", 1)[-1]
        result[normalize(rel)] = row
    return result


def year_from_name(name: str) -> str:
    years = re.findall(r"(?:19|20)\d{2}", name)
    return years[-1] if years else ""


def status_for_group(group: str):
    return {
        "Grupo A": ("ready", "direct_page_extraction"),
        "Grupo B": ("ready_layout_review", "layout_aware_page_extraction"),
        "Grupo C": ("blocked_ocr", "ocr_required"),
        "Grupo D": ("structural_review", "structural_check_then_extract"),
    }.get(group, ("audit_required", "audit_required"))


def count_pages(path: Path) -> int | str:
    if path.suffix.lower() != ".pdf":
        return ""
    try:
        with pdfplumber.open(path) as pdf:
            return len(pdf.pages)
    except Exception:
        return ""


def load_source_manifest() -> dict[str, dict[str, str]]:
    if not SOURCE_MANIFEST.exists():
        return {}
    with SOURCE_MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            normalize(row.get("relative_path", "")): row
            for row in csv.DictReader(handle)
            if row.get("relative_path")
        }


def add_row(rows, path, document_id, source_scope, framework_source,
            country="", country_code="", continent="", role="", validation_status="",
            audit=None, source_manifest=None):
    rel = path.relative_to(CORPUS).as_posix()
    audit = audit or {}
    group = str(audit.get("grupo_analitico", "UNAUDITED"))
    if group == "UNAUDITED" and path.suffix.lower() in {".html", ".htm"}:
       group = "Grupo A"
    page_total = count_pages(path)
    if page_total == "":
        page_total = audit.get("paginas", "")
    rag_status, action = status_for_group(group)
    rows.append({
        "document_id": document_id,
        "source_scope": source_scope,
        "framework_source": framework_source,
        "country": country,
        "country_code": country_code,
        "continent": continent,
        "title": path.stem,
        "year": year_from_name(path.name),
        "language": "",
        "file_name": path.name,
        "source_path": rel,
        "document_role": role,
        "validation_status": validation_status,
        "audit_group": group,
        "audit_status": audit.get("status", ""),
        "pages": page_total,
        "pages_problematic": audit.get("paginas_problematicas", ""),
        "percent_problematic": audit.get("percentual_problematico", ""),
        "source_verified": (source_manifest or {}).get("source_verified", "false"),
        "source_sha256": (source_manifest or {}).get("sha256", ""),
        "needs_ocr": group == "Grupo C",
        "structural_error": group == "Grupo D",
        "rag_ingest_status": rag_status,
        "processing_action": action,
    })


def main():
    if not AUDIT.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {AUDIT}. Execute primeiro rag_project/enrich_document_audit.py"
        )

    registry = load_registry()
    audits = load_audit()
    source_manifest = load_source_manifest()
    rows = []

    # Países: inclui todos os documentos registrados para análise,
    # independentemente de estarem pending_review ou validated.
    for entry in registry.get("countries", []):
        if not entry.get("include_in_analysis", True):
            continue
        country = entry["country"]
        for doc in entry.get("documents", []) or []:
            if doc.get("role") not in {"primary", "complementary"}:
                continue
            path = CORPUS / country / doc["file"]
            if not path.is_file():
                continue
            rel = path.relative_to(CORPUS).as_posix()
            add_row(
                rows, path, doc["document_id"], "national", "",
                country=country,
                country_code=entry.get("country_code", ""),
                continent=entry.get("continent", ""),
                role=doc.get("role", ""),
                validation_status=doc.get("validation_status", ""),
                audit=audits.get(normalize(rel), {}),
                source_manifest=source_manifest.get(normalize(rel), {}),
            )

    df = pd.DataFrame(rows).sort_values(
        ["source_scope", "country", "framework_source", "document_id"]
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    print(f"Catálogo mestre salvo: {OUTPUT}")
    print(f"Documentos: {len(df)}")
    print(df["audit_group"].value_counts(dropna=False))


if __name__ == "__main__":
    main()
