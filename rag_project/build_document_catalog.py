from pathlib import Path
import re
import unicodedata
import pandas as pd

from rag_project.corpus_registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
AUDIT = ROOT / "metadata" / "auditoria" / "auditoria_corpus_classificacao_ABCD.csv"
OUTPUT = ROOT / "metadata" / "documentos.csv"


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


def add_row(rows, path, document_id, source_scope, framework_source,
            country="", country_code="", continent="", role="", validation_status="",
            audit=None):
    rel = path.relative_to(CORPUS).as_posix()
    audit = audit or {}
    group = str(audit.get("grupo_analitico", "UNAUDITED"))
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
        "pages": audit.get("paginas", ""),
        "pages_problematic": audit.get("paginas_problematicas", ""),
        "percent_problematic": audit.get("percentual_problematico", ""),
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
            )

    # Referenciais internacionais: não são países.
    for folder, framework, prefix in [
        ("Unesco", "UNESCO", "UNESCO"),
        ("pisa", "OECD/PISA", "PISA"),
    ]:
        base = CORPUS / folder
        if not base.exists():
            continue
        files = sorted(
            p for p in base.iterdir()
            if p.is_file() and p.suffix.lower() in {".pdf", ".html", ".htm", ".txt"}
        )
        for index, path in enumerate(files, 1):
            rel = path.relative_to(CORPUS).as_posix()
            add_row(
                rows, path, f"{prefix}_{index:03d}",
                "international_reference", framework,
                role="reference",
                validation_status="validated",
                audit=audits.get(normalize(rel), {}),
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
