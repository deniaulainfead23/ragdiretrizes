from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ROOT / "metadata" / "documentos.csv"
PROCESSED = ROOT / "metadata" / "processed_documents.csv"
DEFAULT_OUTPUT = ROOT / "data" / "conteudos.jsonl"

ALLOWED_STATUSES = {
    "ready",
    "ready_with_structural_warning",
    "ready_ocr",
    "ready_ocr_with_page_exception",
}

PAGE_RE = re.compile(r"(?m)^## PAGE\s+(\d+)\s*$")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def split_pages(text: str) -> list[tuple[int, str]]:
    matches = list(PAGE_RE.finditer(text))
    if not matches:
        cleaned = text.strip()
        return [(1, cleaned)] if cleaned else []

    pages: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        page_number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        page_text = text[start:end].strip()
        if page_text:
            pages.append((page_number, page_text))
    return pages


def main(output: str | None = None) -> None:
    output_path = Path(output) if output else DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)

    docs = {row["document_id"]: row for row in read_csv(DOCUMENTS)}
    processed = read_csv(PROCESSED)

    record_count = 0
    document_count = 0

    with output_path.open("w", encoding="utf-8") as handle:
        for item in processed:
            if item.get("status") not in ALLOWED_STATUSES:
                continue

            document_id = item["document_id"]
            document = docs.get(document_id)
            if not document:
                raise ValueError(f"Documento não encontrado no catálogo: {document_id}")

            source = ROOT / item["processed_path"]
            if not source.is_file():
                raise FileNotFoundError(f"Arquivo processado não encontrado: {source}")

            pages = split_pages(source.read_text(encoding="utf-8", errors="ignore"))
            document_count += 1

            for page_number, page_text in pages:
                chunk_id = f"{document_id}_p{page_number:04d}_c001"
                record = {
                    "content_id": chunk_id,
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "country": document.get("country", ""),
                    "source_scope": document.get("source_scope", ""),
                    "framework_source": document.get("framework_source", ""),
                    "document_title": document.get("title", ""),
                    "year": document.get("year", ""),
                    "language": document.get("language", ""),
                    "page_start": page_number,
                    "page_end": page_number,
                    "source_text": page_text,
                    "char_count": len(page_text),
                    "token_estimate": max(1, round(len(page_text) / 4)),
                    "audit_group": document.get("audit_group", ""),
                    "processing_status": item.get("status", ""),
                    "source_path": document.get("source_path", ""),
                    "processed_path": item.get("processed_path", ""),
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                record_count += 1

    print(f"Dataset de conteúdo salvo: {output_path}")
    print(f"Documentos incluídos: {document_count}")
    print(f"Registros/páginas: {record_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera dataset de conteúdo por página a partir dos documentos processados."
    )
    parser.add_argument("--out", default=None, help="Caminho opcional do JSONL de saída.")
    args = parser.parse_args()
    main(args.out)
