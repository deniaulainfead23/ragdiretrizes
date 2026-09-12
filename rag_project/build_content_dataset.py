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


def main(output: str | None = None) -> None:
    output_path = Path(output) if output else DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    docs = {row["document_id"]: row for row in read_csv(DOCUMENTS)}
    processed = read_csv(PROCESSED)

    record_count = 0
    document_count = 0

    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
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
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    print(f"Dataset de conteúdo salvo: {output_path}")
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
