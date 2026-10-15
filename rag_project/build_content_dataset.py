from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from rag_project.paths import DATASET_DIR, METADATA_DIR, INTERMEDIATE_DATA_DIR

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = METADATA_DIR / "documentos.csv"
PROCESSED = METADATA_DIR / "processed_documents.csv"
DEFAULT_OUTPUT = INTERMEDIATE_DATA_DIR / "data" / "conteudos.jsonl"

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


def serialize_jsonl_record(record: dict) -> str:
    """Serializa um registro em uma única linha física de JSONL.

    U+2028 e U+2029 são separadores Unicode que `str.splitlines()` trata como
    quebra de linha. Escapá-los evita que consumidores de JSONL que usam
    `splitlines()` fragmentem um objeto JSON válido no meio de `source_text`.
    """
    return (
        json.dumps(record, ensure_ascii=False)
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def validate_jsonl(path: Path) -> tuple[int, int, int, int]:
    """Valida cada linha JSONL e retorna registros, documentos, IDs únicos e textos vazios."""
    record_count = 0
    document_ids: set[str] = set()
    content_ids: set[str] = set()
    empty_texts = 0

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSONL inválido na linha {line_number}: {exc.msg} "
                    f"(coluna {exc.colno})"
                ) from exc

            record_count += 1
            document_ids.add(str(record.get("document_id", "")))
            content_id = str(record.get("content_id", ""))
            if not content_id:
                raise ValueError(f"Registro sem content_id na linha {line_number}")
            if content_id in content_ids:
                raise ValueError(f"content_id duplicado: {content_id}")
            content_ids.add(content_id)

            if not str(record.get("source_text", "")).strip():
                empty_texts += 1

    return record_count, len(document_ids), len(content_ids), empty_texts


def write_build_report(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "document_id", "processed_path", "source_scope", "validation_status",
        "processing_status", "pages_written", "record_status", "error_type",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(output: str | None = None) -> None:
    output_path = Path(output) if output else DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    report_path = output_path.with_name("dataset_build_report.csv")

    docs = {row["document_id"]: row for row in read_csv(DOCUMENTS)}
    processed = read_csv(PROCESSED)

    record_count = 0
    document_count = 0
    report_rows: list[dict[str, str]] = []

    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            for item in processed:
                document_id = item["document_id"]
                processed_path = item.get("processed_path", "")
                processing_status = item.get("status", "")
                document = docs.get(document_id)
                if not document:
                    report_rows.append({
                        "document_id": document_id, "processed_path": processed_path,
                        "source_scope": "", "validation_status": "",
                        "processing_status": processing_status, "pages_written": "0",
                        "record_status": "missing_document_catalog", "error_type": "MissingDocumentMetadata",
                    })
                    continue
                base_report = {
                    "document_id": document_id,
                    "processed_path": processed_path,
                    "source_scope": document.get("source_scope", ""),
                    "validation_status": document.get("validation_status", ""),
                    "processing_status": processing_status,
                    "pages_written": "0",
                    "record_status": "",
                    "error_type": "",
                }
                if processing_status not in ALLOWED_STATUSES:
                    base_report["record_status"] = "excluded_processing_status"
                    report_rows.append(base_report)
                    continue
                if document.get("source_scope") != "national":
                    base_report["record_status"] = "excluded_non_national"
                    report_rows.append(base_report)
                    continue
                if document.get("validation_status") != "validated":
                    base_report["record_status"] = "excluded_not_previously_verified"
                    report_rows.append(base_report)
                    continue

                source = ROOT / processed_path
                if not source.is_file():
                    base_report["record_status"] = "missing_processed_file"
                    base_report["error_type"] = "FileNotFoundError"
                    report_rows.append(base_report)
                    continue

                try:
                    pages = split_pages(source.read_text(encoding="utf-8", errors="ignore"))
                except OSError as exc:
                    base_report["record_status"] = "processed_file_read_error"
                    base_report["error_type"] = type(exc).__name__
                    report_rows.append(base_report)
                    continue
                if not pages:
                    base_report["record_status"] = "empty_processed_text"
                    base_report["error_type"] = "EmptyProcessedText"
                    report_rows.append(base_report)
                    continue
                document_count += 1
                base_report["pages_written"] = str(len(pages))
                base_report["record_status"] = "included"
                report_rows.append(base_report)

                for page_number, page_text in pages:
                    chunk_id = f"{document_id}_p{page_number:04d}_c001"
                    record = {
                        "content_id": chunk_id,
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "country": document.get("country", ""),
                        "country_code": document.get("country_code", ""),
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
                        "document_role": document.get("document_role", ""),
                        "validation_status": document.get("validation_status", ""),
                        "processing_status": item.get("status", ""),
                        "source_path": document.get("source_path", ""),
                        "processed_path": item.get("processed_path", ""),
                    }
                    handle.write(serialize_jsonl_record(record) + "\n")
                    record_count += 1

        validated_records, validated_documents, unique_ids, empty_texts = validate_jsonl(temp_path)
        if validated_records != record_count:
            raise ValueError(
                f"Contagem divergente após validação: escrito={record_count}, validado={validated_records}"
            )
        if validated_documents != document_count:
            raise ValueError(
                f"Documentos divergentes após validação: processados={document_count}, validados={validated_documents}"
            )

        # Validação adicional compatível com consumidores que usam str.splitlines().
        splitline_records = [
            json.loads(line)
            for line in temp_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(splitline_records) != record_count:
            raise ValueError(
                f"JSONL incompatível com splitlines(): esperado={record_count}, obtido={len(splitline_records)}"
            )

        temp_path.replace(output_path)
    except Exception as exc:
        report_rows.append({
            "document_id": "", "processed_path": "", "source_scope": "",
            "validation_status": "", "processing_status": "",
            "pages_written": "0", "record_status": "generation_failed",
            "error_type": type(exc).__name__,
        })
        write_build_report(report_path, report_rows)
        if temp_path.exists():
            temp_path.unlink()
        raise
    write_build_report(report_path, report_rows)

    print(f"Dataset de conteúdo salvo: {output_path}")
    print(f"Relatório da geração: {report_path}")
    print(f"Documentos incluídos: {document_count}")
    print(f"Registros/páginas: {record_count}")
    print(f"content_id únicos: {unique_ids}")
    print(f"Textos vazios: {empty_texts}")
    print("Validação JSONL: OK")
    print("Compatibilidade splitlines(): OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera dataset de conteúdo por página a partir dos documentos processados."
    )
    parser.add_argument("--out", default=None, help="Caminho opcional do JSONL de saída.")
    args = parser.parse_args()
    main(args.out)
