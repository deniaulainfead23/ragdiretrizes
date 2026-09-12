from __future__ import annotations

"""Auditoria reprodutível do corpus RAG.

O módulo reúne verificações utilizadas no processo de curadoria do corpus:
- consistência do catálogo mestre;
- unicidade de document_id;
- distinção entre fontes nacionais e referências internacionais;
- consistência do manifesto de documentos processados;
- validação de marcadores de página em Markdown;
- detecção de páginas vazias, curtas ou potencialmente ruidosas;
- validação do dataset JSONL de conteúdo;
- geração de relatórios CSV para auditoria humana.

Uso típico:
    python -m rag_project.audit_corpus --all

O script não altera documentos. Ele apenas lê, audita e produz relatórios.
"""

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ROOT / "metadata" / "documentos.csv"
PROCESSED = ROOT / "metadata" / "processed_documents.csv"
CONTENT_JSONL = ROOT / "data" / "conteudos.jsonl"
DEFAULT_REPORT_DIR = ROOT / "analysis" / "audit"

PAGE_RE = re.compile(r"(?m)^## PAGE\s+(\d+)\s*$")
ALLOWED_PROCESSED_STATUSES = {
    "ready",
    "ready_with_structural_warning",
    "ready_ocr",
    "ready_ocr_with_page_exception",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "sim"}


def split_pages(text: str) -> list[tuple[int, str]]:
    matches = list(PAGE_RE.finditer(text))
    if not matches:
        cleaned = text.strip()
        return [(1, cleaned)] if cleaned else []
    pages: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        page = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        pages.append((page, text[start:end].strip()))
    return pages


def text_metrics(text: str) -> dict[str, float | int | str]:
    normalized = text.strip()
    chars = len(normalized)
    if chars == 0 or normalized == "[SEM TEXTO OCR]":
        return {
            "chars": chars,
            "alnum_ratio": 0.0,
            "replacement_chars": normalized.count("�"),
            "status": "EMPTY",
        }
    alnum = sum(ch.isalnum() for ch in normalized)
    ratio = alnum / chars
    replacement_chars = normalized.count("�")
    if chars < 40:
        status = "LOW_TEXT"
    elif ratio < 0.25 or replacement_chars > 0:
        status = "REVIEW_TEXT_QUALITY"
    else:
        status = "OK"
    return {
        "chars": chars,
        "alnum_ratio": round(ratio, 4),
        "replacement_chars": replacement_chars,
        "status": status,
    }


def audit_catalog() -> dict:
    docs = read_csv(DOCUMENTS)
    ids = [row.get("document_id", "").strip() for row in docs]
    duplicate_ids = sorted([doc_id for doc_id, n in Counter(ids).items() if doc_id and n > 1])
    missing_ids = sum(not value for value in ids)

    scope_issues: list[str] = []
    for row in docs:
        doc_id = row.get("document_id", "")
        scope = row.get("source_scope", "").strip()
        country = row.get("country", "").strip()
        framework = row.get("framework_source", "").strip()
        if scope == "national" and not country:
            scope_issues.append(f"{doc_id}: national sem country")
        if scope == "international_reference" and country:
            scope_issues.append(f"{doc_id}: international_reference com country={country}")
        if scope == "international_reference" and not framework:
            scope_issues.append(f"{doc_id}: international_reference sem framework_source")

    return {
        "documents": len(docs),
        "unique_document_ids": len(set(ids)),
        "missing_document_ids": missing_ids,
        "duplicate_document_ids": duplicate_ids,
        "source_scope_counts": dict(Counter(row.get("source_scope", "") for row in docs)),
        "audit_group_counts": dict(Counter(row.get("audit_group", "") for row in docs)),
        "scope_issues": scope_issues,
    }


@dataclass
class PageAudit:
    document_id: str
    processed_path: str
    page: int
    chars: int
    alnum_ratio: float
    replacement_chars: int
    page_status: str


def audit_processed_texts(report_dir: Path) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    processed_rows = read_csv(PROCESSED)
    documents = {r["document_id"]: r for r in read_csv(DOCUMENTS)}
    page_rows: list[PageAudit] = []
    missing_files: list[str] = []
    duplicate_manifest_ids: list[str] = []
    seen: set[str] = set()
    released = 0

    for row in processed_rows:
        document_id = row.get("document_id", "").strip()
        if document_id in seen:
            duplicate_manifest_ids.append(document_id)
        seen.add(document_id)
        if row.get("status", "").strip() not in ALLOWED_PROCESSED_STATUSES:
            continue
        released += 1
        rel_path = row.get("processed_path", "").strip()
        path = ROOT / rel_path
        if not path.is_file():
            missing_files.append(f"{document_id}: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for page, page_text in split_pages(text):
            m = text_metrics(page_text)
            page_rows.append(PageAudit(
                document_id=document_id,
                processed_path=rel_path,
                page=page,
                chars=int(m["chars"]),
                alnum_ratio=float(m["alnum_ratio"]),
                replacement_chars=int(m["replacement_chars"]),
                page_status=str(m["status"]),
            ))

    page_csv = report_dir / "processed_page_audit.csv"
    with page_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(asdict(page_rows[0]).keys()) if page_rows else [
            "document_id", "processed_path", "page", "chars", "alnum_ratio",
            "replacement_chars", "page_status"
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in page_rows:
            writer.writerow(asdict(row))

    by_status = Counter(row.page_status for row in page_rows)
    docs_with_review_pages = sorted({
        row.document_id for row in page_rows if row.page_status != "OK"
    })

    return {
        "manifest_rows": len(processed_rows),
        "released_documents": released,
        "catalog_documents": len(documents),
        "missing_processed_files": missing_files,
        "duplicate_manifest_ids": sorted(set(duplicate_manifest_ids)),
        "audited_pages": len(page_rows),
        "page_status_counts": dict(by_status),
        "documents_with_review_pages": docs_with_review_pages,
        "page_report": str(page_csv.relative_to(ROOT)),
    }


def audit_jsonl(path: Path = CONTENT_JSONL) -> dict:
    if not path.is_file():
        return {"exists": False, "path": str(path)}
    records = 0
    document_ids: set[str] = set()
    content_ids: set[str] = set()
    duplicate_ids: list[str] = []
    empty_texts = 0
    malformed: list[dict[str, str | int]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                malformed.append({
                    "line": line_number,
                    "error": f"{exc.msg} (coluna {exc.colno})",
                })
                continue
            records += 1
            document_ids.add(str(row.get("document_id", "")))
            content_id = str(row.get("content_id", ""))
            if content_id in content_ids:
                duplicate_ids.append(content_id)
            content_ids.add(content_id)
            if not str(row.get("source_text", "")).strip():
                empty_texts += 1

    return {
        "exists": True,
        "path": str(path.relative_to(ROOT)),
        "records": records,
        "unique_documents": len(document_ids),
        "unique_content_ids": len(content_ids),
        "duplicate_content_ids": sorted(set(duplicate_ids)),
        "empty_source_text": empty_texts,
        "malformed_json_lines": malformed,
    }


def write_summary(report_dir: Path, payload: dict) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "audit_summary.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditoria reprodutível do corpus RAG")
    parser.add_argument("--catalog", action="store_true", help="Audita metadata/documentos.csv")
    parser.add_argument("--processed", action="store_true", help="Audita textos processados por página")
    parser.add_argument("--jsonl", action="store_true", help="Audita data/conteudos.jsonl")
    parser.add_argument("--all", action="store_true", help="Executa todas as auditorias")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    if not any([args.catalog, args.processed, args.jsonl, args.all]):
        args.all = True

    report_dir = Path(args.report_dir)
    payload: dict[str, dict] = {}
    if args.all or args.catalog:
        payload["catalog"] = audit_catalog()
    if args.all or args.processed:
        payload["processed_texts"] = audit_processed_texts(report_dir)
    if args.all or args.jsonl:
        payload["content_jsonl"] = audit_jsonl()

    summary = write_summary(report_dir, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nRelatório: {summary}")


if __name__ == "__main__":
    main()
