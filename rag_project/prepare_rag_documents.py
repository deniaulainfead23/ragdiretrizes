from pathlib import Path
import csv
import pandas as pd

from rag_project.rag.ingest import extract_pdf_pages

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
CATALOG = ROOT / "metadata" / "documentos.csv"
OUTPUT_DIR = ROOT / "corpus" / "processed"
MANIFEST = ROOT / "metadata" / "processed_documents.csv"


def text_pages(path: Path):
    if path.suffix.lower() == ".pdf":
        return extract_pdf_pages(str(path))
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = path.read_text(encoding="latin-1", errors="ignore")
    return [(1, text)] if text.strip() else []


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)


def main():
    df = pd.read_csv(CATALOG).fillna("")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows = []

    for row in df.to_dict("records"):
        group = row["audit_group"]

        # Grupo C fica explicitamente bloqueado até OCR validado.
        if group == "Grupo C":
            manifest_rows.append({
                "document_id": row["document_id"],
                "status": "blocked_ocr",
                "processed_path": "",
                "pages_extracted": 0,
                "notes": "OCR obrigatório antes da indexação.",
            })
            continue

        source = CORPUS / row["source_path"]
        if not source.exists():
            manifest_rows.append({
                "document_id": row["document_id"],
                "status": "missing_source",
                "processed_path": "",
                "pages_extracted": 0,
                "notes": str(source),
            })
            continue

        pages = text_pages(source)
        if not pages:
            manifest_rows.append({
                "document_id": row["document_id"],
                "status": "no_text",
                "processed_path": "",
                "pages_extracted": 0,
                "notes": "Nenhum texto extraível.",
            })
            continue

        scope = row["country"] or row["framework_source"] or "reference"
        target_dir = OUTPUT_DIR / safe_name(scope)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{safe_name(row['document_id'])}.md"

        header = [
            f"# {row['title']}",
            "",
            f"- document_id: {row['document_id']}",
            f"- source_scope: {row['source_scope']}",
            f"- framework_source: {row['framework_source']}",
            f"- country: {row['country']}",
            f"- year: {row['year']}",
            f"- audit_group: {group}",
            f"- source_path: {row['source_path']}",
            "",
        ]

        body = list(header)
        for page_number, text in pages:
            body.extend([
                f"## PAGE {page_number}",
                "",
                text.strip(),
                "",
            ])

        target.write_text("\n".join(body), encoding="utf-8")
        manifest_rows.append({
            "document_id": row["document_id"],
            "status": "ready" if group in {"Grupo A", "Grupo B"} else "ready_with_structural_warning",
            "processed_path": target.relative_to(ROOT).as_posix(),
            "pages_extracted": len(pages),
            "notes": "Layout complexo" if group == "Grupo B" else ("Aviso estrutural" if group == "Grupo D" else ""),
        })

    pd.DataFrame(manifest_rows).to_csv(MANIFEST, index=False, encoding="utf-8-sig")
    print(f"Documentos preparados em: {OUTPUT_DIR}")
    print(f"Manifesto: {MANIFEST}")


if __name__ == "__main__":
    main()
