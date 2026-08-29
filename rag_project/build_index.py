"""Script para construir o índice vetorial a partir da pasta `corpus/`.

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

from rag.ingest import iter_corpus_documents
from rag.indexer import Indexer
from rag.preprocess import chunk_text, normalize_text

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
            "marrocos": "Marrocos",
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
    for _ in iter_corpus_documents(str(root)):
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

    for doc_index, (rel_path, file_path, text, ext) in enumerate(iter_corpus_documents(str(root)), start=1):
        if max_documents is not None and processed_count >= max_documents:
            break
        if rel_path in processed or rel_path in failed:
            print(f"[skip] {rel_path} já processado / registrado.")
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
                from rag.ingest import extract_pdf_pages
                pages = extract_pdf_pages(file_path)
                if not pages:
                    raise ValueError("Nenhuma página extraída do PDF")
                for page_number, page_text in pages:
                    normalized_page = normalize_text(page_text)
                    for chunk_index, chunk in enumerate(chunk_text(normalized_page, chunk_size=chunk_size, overlap=overlap)):
                        if max_chunks_per_doc is not None and chunk_count >= max_chunks_per_doc:
                            break
                        batch_texts.append(chunk)
                        batch_metas.append(build_document_metadata(rel_path, chunk_index, page_number, chunk))
                        chunk_count += 1
                        if len(batch_texts) >= embedding_batch_size:
                            idx.add_batch(batch_texts, batch_metas, batch_size=min(embedding_batch_size, len(batch_texts)))
                            batch_texts = []
                            batch_metas = []
                    if max_chunks_per_doc is not None and chunk_count >= max_chunks_per_doc:
                        break
            else:
                normalized = normalize_text(text)
                for chunk_index, chunk in enumerate(chunk_text(normalized, chunk_size=chunk_size, overlap=overlap)):
                    if max_chunks_per_doc is not None and chunk_count >= max_chunks_per_doc:
                        break
                    batch_texts.append(chunk)
                    batch_metas.append(build_document_metadata(rel_path, chunk_index, "", chunk))
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
        idx2 = Indexer(); idx2.load(str(out))
        print(f"Índice salvo em: {out / 'index.faiss'}")
        print(f"Metadados salvos em: {out / 'metadatas.json'}")
        print(f"Vetores no índice: {idx2.index.ntotal}")
        print(f"Registros de metadados: {len(idx2.metadatas)}")
        if idx2.index.ntotal != len(idx2.metadatas):
            raise RuntimeError(f"Índice desalinhado: ntotal={idx2.index.ntotal}, metadados={len(idx2.metadatas)}")


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
