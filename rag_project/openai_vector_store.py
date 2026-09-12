"""Upload e consultas RAG usando Vector Stores hospedados pela OpenAI."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from rag_project.vector_backend import write_vector_backend_manifest


DEFAULT_MODEL = "gpt-4o-mini"
ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path(__file__).resolve().parent / ".openai_vector_stores.json"
DOCUMENT_CATALOG_PATH = ROOT / "metadata" / "documentos.csv"
PROCESSED_MANIFEST_PATH = ROOT / "metadata" / "processed_documents.csv"

ALLOWED_PROCESSED_STATUSES = {
    "ready",
    "ready_with_structural_warning",
    "ready_ocr",
    "ready_ocr_with_page_exception",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _attributes_from_row(document: dict[str, str], processed: dict[str, str]) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "document_id": document.get("document_id", ""),
        "country": document.get("country", ""),
        "source_scope": document.get("source_scope", ""),
        "framework_source": document.get("framework_source", ""),
        "audit_group": document.get("audit_group", ""),
        "year": document.get("year", ""),
        "validation_status": document.get("validation_status", ""),
        "processing_status": processed.get("status", ""),
    }
    return {key: value for key, value in raw.items() if str(value).strip()}


def iter_processed_documents(
    document_catalog: Path = DOCUMENT_CATALOG_PATH,
    processed_manifest: Path = PROCESSED_MANIFEST_PATH,
):
    """Cruza catálogo mestre e manifesto de processamento e libera só os status aceitos."""
    documents = {
        row["document_id"]: row
        for row in _read_csv(document_catalog)
        if row.get("document_id")
    }
    processed_rows = _read_csv(processed_manifest)

    seen: set[str] = set()
    for processed in processed_rows:
        document_id = processed.get("document_id", "").strip()
        if not document_id:
            continue
        if document_id in seen:
            raise ValueError(f"document_id duplicado em {processed_manifest}: {document_id}")
        seen.add(document_id)

        status = processed.get("status", "").strip()
        if status not in ALLOWED_PROCESSED_STATUSES:
            continue

        document = documents.get(document_id)
        if document is None:
            raise ValueError(
                f"{document_id} está em {processed_manifest}, mas não existe em {document_catalog}"
            )

        rel_path = processed.get("processed_path", "").strip()
        if not rel_path:
            raise ValueError(f"{document_id} está liberado, mas não possui processed_path")

        source_path = ROOT / rel_path
        if not source_path.is_file():
            raise FileNotFoundError(
                f"Arquivo processado não encontrado para {document_id}: {source_path}"
            )

        yield document, processed, source_path


def validate_processed_corpus(
    document_catalog: Path = DOCUMENT_CATALOG_PATH,
    processed_manifest: Path = PROCESSED_MANIFEST_PATH,
):
    rows = list(iter_processed_documents(document_catalog, processed_manifest))
    if not rows:
        raise RuntimeError("Nenhum documento processado foi liberado para indexação.")

    print(f"Documentos liberados para indexação: {len(rows)}")
    print(f"document_id únicos: {len({d['document_id'] for d, _, _ in rows})}")

    by_status: dict[str, int] = defaultdict(int)
    by_scope: dict[str, int] = defaultdict(int)
    for document, processed, _ in rows:
        by_status[processed["status"]] += 1
        by_scope[document.get("source_scope") or "unknown"] += 1

    print("Por status:")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")

    print("Por source_scope:")
    for scope, count in sorted(by_scope.items()):
        print(f"  {scope}: {count}")

    return rows


def _upload_jsonl_by_country(client: OpenAI, vector_store_id: str, file_path: Path) -> None:
    """Compatibilidade com datasets JSONL legados."""
    records_by_country: dict[str, list[str]] = defaultdict(list)
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        country = record.get("country")
        if not country:
            raise ValueError(f"Registro sem country em {file_path}")
        records_by_country[country].append(line)

    for country, records in sorted(records_by_country.items()):
        content = ("\n".join(records) + "\n").encode("utf-8")
        uploaded = client.vector_stores.files.upload_and_poll(
            vector_store_id=vector_store_id,
            file=(f"{file_path.stem}_{country}.txt", BytesIO(content)),
            attributes={"country": country},
        )
        if uploaded.status != "completed":
            raise RuntimeError(f"Falha ao indexar {country}: {uploaded.status}")
        print(f"Arquivo indexado para {country}: {uploaded.id}")


def upload_dataset(file_path: str, vector_store_name: str, api_key: str | None = None) -> str:
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    vector_store = client.vector_stores.create(name=vector_store_name)
    source_path = Path(file_path)

    if source_path.suffix.lower() == ".jsonl":
        _upload_jsonl_by_country(client, vector_store.id, source_path)
    else:
        with source_path.open("rb") as handle:
            uploaded = client.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store.id,
                file=(source_path.name, handle),
            )
        if uploaded.status != "completed":
            raise RuntimeError(f"Falha ao indexar arquivo: {uploaded.status}")
        print(f"Arquivo indexado: {uploaded.id}")

    print(f"vector_store_id={vector_store.id}")
    return vector_store.id


def upload_processed_corpus(
    vector_store_name: str = "ragdiretrizes-processed-corpus",
    api_key: str | None = None,
    document_catalog: Path = DOCUMENT_CATALOG_PATH,
    processed_manifest: Path = PROCESSED_MANIFEST_PATH,
) -> str:
    """Indexa somente arquivos processados e liberados no manifesto."""
    rows = validate_processed_corpus(document_catalog, processed_manifest)
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    vector_store = client.vector_stores.create(name=vector_store_name)

    for position, (document, processed, source_path) in enumerate(rows, start=1):
        document_id = document["document_id"]
        attributes = _attributes_from_row(document, processed)

        with source_path.open("rb") as handle:
            uploaded = client.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store.id,
                file=(f"{document_id}__{source_path.name}", handle),
                attributes=attributes,
            )

        if uploaded.status != "completed":
            raise RuntimeError(
                f"Falha ao indexar {document_id} / {source_path.name}: {uploaded.status}"
            )

        label = document.get("country") or document.get("framework_source") or "sem-escopo"
        print(f"[{position}/{len(rows)}] {document_id} | {label} | {uploaded.id}")

    print(f"vector_store_id={vector_store.id}")
    return vector_store.id


def sync_processed_corpus(
    api_key: str | None = None,
    replace: bool = False,
    vector_store_name: str = "ragdiretrizes-processed-corpus",
) -> str:
    manifest = _load_manifest()
    existing = manifest.get("processed", {}).get("vector_store_id")

    if existing and not replace:
        print(f"Reutilizando Vector Store existente: {existing}")
        return existing

    vector_store_id = upload_processed_corpus(
        vector_store_name=vector_store_name,
        api_key=api_key,
    )

    manifest["processed"] = {
        "vector_store_id": vector_store_id,
        "document_catalog": str(DOCUMENT_CATALOG_PATH.relative_to(ROOT)),
        "processed_manifest": str(PROCESSED_MANIFEST_PATH.relative_to(ROOT)),
        "allowed_statuses": sorted(ALLOWED_PROCESSED_STATUSES),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _save_manifest(manifest)

    write_vector_backend_manifest({
        "backend": "openai",
        "vector_store_id": vector_store_id,
        "model": DEFAULT_MODEL,
        "index_folder": "corpus/processed + corpus/processed_ocr",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })

    print(f"Manifesto local: {MANIFEST_PATH}")
    return vector_store_id


def _query_filter(country: str = "", framework: str = "") -> dict | None:
    if country and framework:
        raise ValueError("Use country ou framework, não ambos na mesma consulta.")
    if country:
        return {"type": "eq", "key": "country", "value": country}
    if framework:
        return {"type": "eq", "key": "framework_source", "value": framework}
    return None


def cloud_rag_query(
    vector_store_id: str,
    question: str,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    question_id: str = "",
    country: str = "",
    framework: str = "",
    category_id: str = "",
) -> str:
    print("[1/4] Recebendo pergunta...")
    print(f"[2/4] Buscando documentos no Vector Store {vector_store_id}...")

    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    tool: dict[str, Any] = {
        "type": "file_search",
        "vector_store_ids": [vector_store_id],
        "max_num_results": 8,
    }
    query_filter = _query_filter(country, framework)
    if query_filter is not None:
        tool["filters"] = query_filter

    response = client.responses.create(
        model=model,
        input=(
            "Responda em português usando somente as evidências recuperadas.\n"
            "Retorne JSON com: question_id, country, response, evidence_ids, "
            "evidence_classification, validation_status.\n"
            "Para cada evidência, informe document_id, documento, página, "
            "trecho original, classificação e validation_status.\n"
            f"question_id: {question_id}\n"
            f"country: {country}\n"
            f"framework: {framework}\n"
            f"category_id: {category_id}\n"
            f"Pergunta: {question}"
        ),
        tools=[tool],
    )

    print("[3/4] Encontrados trechos relevantes para a consulta.")
    print("[4/4] Gerando resposta...")
    return response.output_text


def sync_dataset(
    file_path: str,
    dataset_name: str,
    existing_id: str | None = None,
    api_key: str | None = None,
    replace: bool = False,
) -> str:
    """Compatibilidade com datasets JSONL antigos. Não é o fluxo recomendado."""
    manifest = _load_manifest()
    vector_store_id = None if replace else existing_id or manifest.get(dataset_name, {}).get("vector_store_id")
    if not vector_store_id:
        vector_store_id = upload_dataset(file_path, f"ragdiretrizes-{dataset_name}", api_key)

    manifest[dataset_name] = {
        "vector_store_id": vector_store_id,
        "file": str(Path(file_path)),
    }
    _save_manifest(manifest)

    write_vector_backend_manifest({
        "backend": "openai",
        "vector_store_id": vector_store_id,
        "model": DEFAULT_MODEL,
        "index_folder": str(Path(file_path).parent),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    print(f"{dataset_name}: vector_store_id={vector_store_id}")
    return vector_store_id


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Hospeda o corpus processado na OpenAI e consulta com File Search."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "validate-processed",
        help="Valida os manifestos e caminhos sem fazer upload.",
    )

    processed_parser = subparsers.add_parser(
        "sync-processed",
        help="Indexa somente documentos processados e liberados.",
    )
    processed_parser.add_argument("--openai_key", default=None)
    processed_parser.add_argument(
        "--replace",
        action="store_true",
        help="Cria um novo Vector Store mesmo se já houver um registrado.",
    )
    processed_parser.add_argument(
        "--name",
        default="ragdiretrizes-processed-corpus",
        help="Nome do Vector Store.",
    )

    upload_parser = subparsers.add_parser(
        "upload",
        help="Fluxo legado: cria Vector Store e indexa um arquivo/dataset.",
    )
    upload_parser.add_argument("--file", required=True)
    upload_parser.add_argument("--name", default="ragdiretrizes-corpus")
    upload_parser.add_argument("--openai_key", default=None)

    query_parser = subparsers.add_parser(
        "query",
        help="Consulta um Vector Store com File Search.",
    )
    query_parser.add_argument("--vector_store_id", required=True)
    query_parser.add_argument("--question", required=True)
    query_parser.add_argument("--openai_key", default=None)
    query_parser.add_argument("--country", default="")
    query_parser.add_argument("--framework", default="")
    query_parser.add_argument("--question_id", default="")
    query_parser.add_argument("--category_id", default="")

    sync_parser = subparsers.add_parser(
        "sync",
        help="Fluxo legado de datasets JSONL.",
    )
    sync_parser.add_argument("--original", default="../corpus/dataset_output/dataset_original.jsonl")
    sync_parser.add_argument("--english", default="../corpus/dataset_output/dataset_english.jsonl")
    sync_parser.add_argument("--english-vector-store-id", default=None)
    sync_parser.add_argument("--openai_key", default=None)
    sync_parser.add_argument("--replace", action="store_true")
    sync_parser.add_argument(
        "--dataset",
        choices=["original", "english", "both"],
        default="both",
    )

    args = parser.parse_args()

    if args.command == "validate-processed":
        validate_processed_corpus()
    elif args.command == "sync-processed":
        sync_processed_corpus(
            api_key=args.openai_key,
            replace=args.replace,
            vector_store_name=args.name,
        )
    elif args.command == "upload":
        upload_dataset(args.file, args.name, args.openai_key)
    elif args.command == "query":
        print(cloud_rag_query(
            args.vector_store_id,
            args.question,
            api_key=args.openai_key,
            question_id=args.question_id,
            country=args.country,
            framework=args.framework,
            category_id=args.category_id,
        ))
    elif args.command == "sync":
        if args.dataset in {"original", "both"}:
            sync_dataset(
                args.original,
                "original",
                api_key=args.openai_key,
                replace=args.replace,
            )
        if args.dataset in {"english", "both"}:
            sync_dataset(
                args.english,
                "english",
                existing_id=args.english_vector_store_id,
                api_key=args.openai_key,
                replace=args.replace,
            )


if __name__ == "__main__":
    main()
