"""Script para construir o índice vetorial a partir de `dados_brutos/corpus/`.

Uso:
    python build_index.py --corpus ../corpus --out indexed
"""
import argparse
import gc
import json
import os
import re
import time
from pathlib import Path

try:
    from rag_project.rag.ingest import extract_pdf_pages, iter_corpus_files, read_text_file
    from rag_project.rag.indexer import Indexer
    from rag_project.rag.preprocess import chunk_text, normalize_text
except ImportError:  # pragma: no cover - suporte ao uso legado de dentro de rag_project
    from rag.ingest import extract_pdf_pages, iter_corpus_files, read_text_file
    from rag.indexer import Indexer
    from rag.preprocess import chunk_text, normalize_text
from rag_project.corpus_registry import load_registry, registered_documents

EMBEDDING_BATCH_SIZE = 16


def infer_country_from_path(rel_path: str) -> str:
    path = Path(rel_path)
    country = ""
    if path.parts:
        candidate = path.parts[0].strip().lower()
        mapping = {
            "africa-do-sul": "África do Sul",
            "australia": "Austrália",
            "brasil": "Brasil",
            "canada": "Canadá",
            "chile": "Chile",
            "coreia-do-sul": "Coreia do Sul",
            "estonia": "Estônia",
            "eua": "Estados Unidos",
            "finlandia": "Finlândia",
            "gana": "Gana",
            "hong-kong": "Hong Kong",
            "irlanda": "Irlanda",
            "japao": "Japão",
            "nova-zelandia": "Nova Zelândia",
            "quenia": "Quênia",
            "reino-unido": "Reino Unido",
            "ruanda": "Ruanda",
            "singapura": "Singapura",
            "suica": "Suíça",
            "taiwan": "Taiwan",
            "uruguai": "Uruguai",
        }
        country = mapping.get(candidate, "")
    return country


def infer_year_from_path(rel_path: str) -> str:
    matches = re.findall(r"(19\d{2}|20\d{2})", rel_path)
    return matches[0] if matches else ""


def infer_document_type(rel_path: str) -> str:
    lower = rel_path.lower()
    if "curriculo" in lower or "currículo" in lower:
        return "currículo"
    if "bncc" in lower:
        return "base curricular"
    if "compet" in lower:
        return "competência"
    if "tecnologia" in lower:
        return "tecnologia"
    if "pol" in lower:
        return "política"
    if lower.endswith(".pdf"):
        return "documento"
    return ""


def load_checkpoint(checkpoint_path: Path):
    if not checkpoint_path.exists():
        return {"processed_documents": [], "failed_documents": []}
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"processed_documents": [], "failed_documents": []}


def save_checkpoint(checkpoint_path: Path, payload):
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def build_document_metadata(rel_path: str, chunk_id: int, page_number: int | str = "", text: str = "") -> dict:
    filename = Path(rel_path).name
    stem = Path(rel_path).stem
    return {
        "source": rel_path,
        "path": rel_path,
        "filename": filename,
        "chunk_id": chunk_id,
        "page": page_number,
        "country": infer_country_from_path(rel_path),
        "year": infer_year_from_path(rel_path),
        "title": stem,
        "document_type": infer_document_type(rel_path),
        "text": text,
    }


def build(corpus_dir: str, out_dir: str, chunk_size: int = 1200, overlap: int = 200, max_chunks_per_doc: int | None = None, max_documents: int | None = None, embedding_batch_size: int = EMBEDDING_BATCH_SIZE, verbose: bool = False):
    root = Path(corpus_dir)
    out = Path(out_dir)
    registry = load_registry()
    registered = {(entry["country"], document["file"]): (entry, document) for entry, document in registered_documents(registry)}
    checkpoint_path = out / "checkpoint.json"
    checkpoint = load_checkpoint(checkpoint_path)
    processed = set(checkpoint.get("processed_documents", []))
    failed = set(checkpoint.get("failed_documents", []))

    idx = Indexer()
    if (out / "index.faiss").exists() and (out / "metadatas.json").exists():
        try:
            idx.load(str(out))
            print(f"Resumindo índice existente em {out}. Já carregados {len(idx.metadatas)} vetores.")
        except Exception as exc:
            print(f"Aviso: não foi possível carregar o índice existente ({exc}). Reiniciando do zero.")
            idx = Indexer()
            processed = set()
            failed = set()

    total_documents = 0
    for rel_path, _, _ in iter_corpus_files(str(root)):
        country = Path(rel_path).parts[0] if Path(rel_path).parts else ""
        filename = Path(rel_path).name
        if (country, filename) in registered:
            total_documents += 1

    if verbose:
        print(f"Ingesting corpus from {root}... Total de documentos encontrados: {total_documents}")
    else:
        print(f"Ingesting corpus from {root}... Total de documentos encontrados: {total_documents}")

    if max_documents is not None:
        print(f"Limite de teste: {max_documents} documento(s) no processamento atual.")

    processed_count = 0
    failed_files = []
    total_chunks = 0
    doc_start_total = time.time()

    doc_index = 0
    for rel_path, file_path, ext in iter_corpus_files(str(root)):
        country_folder = Path(rel_path).parts[0] if Path(rel_path).parts else ""
        filename = Path(rel_path).name
        registry_item = registered.get((country_folder, filename))
        if registry_item is None:
            continue
        country_entry, document = registry_item
        if max_documents is not None and processed_count >= max_documents:
            break
        if rel_path in processed or rel_path in failed:
            print(f"[skip] {rel_path} já processado / registrado.")
            continue
        doc_index += 1
        if ext != ".pdf" and not read_text_file(file_path).strip():
            continue

        if verbose:
            print(f"\n[{doc_index}/{total_documents}] Processando documento: {rel_path}")
        else:
            print(f"\n[{doc_index}/{total_documents}] Processando documento: {rel_path}")

        doc_start = time.time()
        batch_texts = []
        batch_metas = []
        chunk_count = 0
        doc_failed = False

        try:
            if ext == ".pdf":
                pages = extract_pdf_pages(file_path)
                if not pages:
                    raise ValueError("Nenhuma página extraída do PDF")
                for page_number, page_text in pages:
                    normalized_page = normalize_text(page_text)
                    for chunk_index, chunk in enumerate(chunk_text(normalized_page, chunk_size=chunk_size, overlap=overlap)):
                        if max_chunks_per_doc is not None and chunk_count >= max_chunks_per_doc:
                            break
                        batch_texts.append(chunk)
                        metadata = build_document_metadata(rel_path, chunk_index, page_number, chunk)
                        metadata.update({"country_code": country_entry["country"], "document_id": document["document_id"], "document_role": document["role"], "validation_status": document["validation_status"], "corpus_version": registry["corpus_version"]})
                        batch_metas.append(metadata)
                        chunk_count += 1
                        if len(batch_texts) >= embedding_batch_size:
                            idx.add_batch(batch_texts, batch_metas, batch_size=min(embedding_batch_size, len(batch_texts)))
                            batch_texts = []
                            batch_metas = []
                    if max_chunks_per_doc is not None and chunk_count >= max_chunks_per_doc:
                        break
            else:
                normalized = normalize_text(read_text_file(file_path))
                for chunk_index, chunk in enumerate(chunk_text(normalized, chunk_size=chunk_size, overlap=overlap)):
                    if max_chunks_per_doc is not None and chunk_count >= max_chunks_per_doc:
                        break
                    batch_texts.append(chunk)
                    metadata = build_document_metadata(rel_path, chunk_index, "", chunk)
                    metadata.update({"country_code": country_entry["country"], "document_id": document["document_id"], "document_role": document["role"], "validation_status": document["validation_status"], "corpus_version": registry["corpus_version"]})
                    batch_metas.append(metadata)
                    chunk_count += 1
                    if len(batch_texts) >= embedding_batch_size:
                        idx.add_batch(batch_texts, batch_metas, batch_size=min(embedding_batch_size, len(batch_texts)))
                        batch_texts = []
                        batch_metas = []

            if batch_texts:
                idx.add_batch(batch_texts, batch_metas, batch_size=min(embedding_batch_size, len(batch_texts)))

            if not idx.validate_alignment():
                raise RuntimeError(f"Alinhamento inválido pós-processamento: FAISS={idx.index.ntotal}, metadados={len(idx.metadatas)}")

            idx.save(str(out))
            processed.add(rel_path)
            checkpoint["processed_documents"] = sorted(processed)
            checkpoint["failed_documents"] = sorted(failed)
            checkpoint["total_documents_seen"] = total_documents
            checkpoint["last_processed_document"] = rel_path
            checkpoint["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_checkpoint(checkpoint_path, checkpoint)

            total_chunks += chunk_count
            processed_count += 1
            elapsed = time.time() - doc_start
            print(f"Chunks criados: {chunk_count}")
            print(f"Documento concluído: {rel_path}")
            print(f"tempo do documento: {elapsed:.1f}s | tempo total: {time.time() - doc_start_total:.1f}s")
            print("Checkpoint salvo.")
            del batch_texts, batch_metas
            gc.collect()

        except Exception as exc:
            doc_failed = True
            failed.add(rel_path)
            failed_files.append(rel_path)
            checkpoint["failed_documents"] = sorted(failed)
            checkpoint["processed_documents"] = sorted(processed)
            save_checkpoint(checkpoint_path, checkpoint)
            print(f"Erro ao processar {rel_path}: {exc}")

        if doc_failed:
            print(f"Arquivo falhou e foi registrado em 'failed_documents': {rel_path}")

    print("\nResumo final:")
    print(f"Documentos processados com sucesso: {len(processed)}")
    print(f"Documentos falharam: {len(failed)}")
    if failed_files:
        print("Arquivos com falha:")
        for file in failed_files:
            print(f" - {file}")

    if os.path.exists(out / "index.faiss") and os.path.exists(out / "metadatas.json"):
        print(f"Índice salvo em: {out / 'index.faiss'}")
        print(f"Metadados salvos em: {out / 'metadatas.json'}")
        print(f"Vetores no índice: {idx.index.ntotal}")
        print(f"Registros de metadados: {len(idx.metadatas)}")
        if idx.index.ntotal != len(idx.metadatas):
            raise RuntimeError(f"Índice desalinhado: ntotal={idx.index.ntotal}, metadados={len(idx.metadatas)}")
    
def build_from_dataset(
    dataset_path: str,
    out_dir: str,
    chunk_size: int = 1200,
    overlap: int = 200,
    embedding_batch_size: int = EMBEDDING_BATCH_SIZE,
) -> dict:
    """Build a fresh FAISS index from validated, page-level dataset JSONL."""
    dataset_file = Path(dataset_path)
    output_dir = Path(out_dir)
    indexer = Indexer()
    batch_texts: list[str] = []
    batch_metadata: list[dict] = []
    pages_used = 0
    chunks_used = 0
    excluded_records = 0

    with dataset_file.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL inválido na linha {line_number}: {exc.msg}") from exc

            if record.get("source_scope") != "national" or record.get("validation_status") != "validated":
                excluded_records += 1
                continue
            page_text = str(record.get("source_text", "")).strip()
            if not page_text:
                excluded_records += 1
                continue

            pages_used += 1
            source_path = str(record.get("source_path", ""))
            normalized_page = normalize_text(page_text)
            for chunk_index, chunk in enumerate(
                chunk_text(normalized_page, chunk_size=chunk_size, overlap=overlap)
            ):
                page_number = record.get("page_start", "")
                metadata = {
                    "source": source_path,
                    "path": source_path,
                    "filename": Path(source_path).name,
                    "chunk_id": f"{record.get('content_id', record.get('chunk_id', ''))}_c{chunk_index + 1:03d}",
                    "content_id": record.get("content_id", ""),
                    "document_id": record.get("document_id", ""),
                    "country": record.get("country", ""),
                    "country_code": record.get("country_code", ""),
                    "document_role": record.get("document_role", ""),
                    "validation_status": record.get("validation_status", ""),
                    "processing_status": record.get("processing_status", ""),
                    "source_scope": record.get("source_scope", ""),
                    "year": record.get("year", ""),
                    "page": page_number,
                    "page_start": page_number,
                    "page_end": record.get("page_end", page_number),
                    "title": record.get("document_title", ""),
                    "language": record.get("original_language") or record.get("language", ""),
                    "retrieval_language": "en" if record.get("translation_status") == "translated" else record.get("language", ""),
                    "translation_status": record.get("translation_status", "not_available"),
                    "text": chunk,
                    "translated_text_en": chunk,
                    "source_text": str(record.get("original_text", "")).strip() or chunk,
                }
                batch_texts.append(chunk)
                batch_metadata.append(metadata)
                chunks_used += 1
                if len(batch_texts) >= embedding_batch_size:
                    indexer.add_batch(batch_texts, batch_metadata, batch_size=embedding_batch_size)
                    batch_texts = []
                    batch_metadata = []

    if batch_texts:
        indexer.add_batch(batch_texts, batch_metadata, batch_size=embedding_batch_size)
    if not indexer.validate_alignment():
        raise RuntimeError(
            f"Índice desalinhado: vetores={indexer.index.ntotal}, metadados={len(indexer.metadatas)}"
        )
    if not pages_used:
        raise ValueError("Dataset sem páginas nacionais previamente validadas; índice não criado")

    indexer.save(str(output_dir))
    result = {
        "dataset_path": str(dataset_file),
        "index_path": str(output_dir),
        "pages_indexed": pages_used,
        "chunks_indexed": chunks_used,
        "records_excluded": excluded_records,
        "embedding_model": MODEL_NAME,
        "vector_count": int(indexer.index.ntotal),
        "metadata_count": len(indexer.metadatas),
    }
    checkpoint_path = output_dir / "build_report.json"
    checkpoint_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', default='../corpus', help='Pasta do corpus')
    parser.add_argument('--out', default='indexed', help='Pasta de saída do índice')
    parser.add_argument('--chunk-size', type=int, default=1200, help='Tamanho (caracteres) de cada chunk')
    parser.add_argument('--overlap', type=int, default=200, help='Overlap (caracteres) entre chunks')
    parser.add_argument('--max-chunks-per-doc', type=int, default=None, help='Máximo de chunks por documento (útil para debug)')
    parser.add_argument('--max-documents', type=int, default=None, help='Limita execução para N documentos (teste controlado)')
    parser.add_argument('--embedding-batch-size', type=int, default=EMBEDDING_BATCH_SIZE, help='Quantidade de chunks por lote de embeddings')
    parser.add_argument('--verbose', action='store_true', help='Habilita logs de progresso detalhados')
    args = parser.parse_args()
    build(
        args.corpus,
        args.out,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        max_chunks_per_doc=args.max_chunks_per_doc,
        max_documents=args.max_documents,
        embedding_batch_size=args.embedding_batch_size,
        verbose=args.verbose,
    )


if __name__ == '__main__':
    main()
