"""Indexa um único arquivo PDF para teste rápido."""
import argparse
import os
from pathlib import Path
from rag.ingest import extract_text_from_pdf
from rag.preprocess import normalize_text, chunk_text
from rag.indexer import Indexer

def build_single(pdf_path: str, out_dir: str):
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(pdf_path)
    text = extract_text_from_pdf(str(p))
    norm = normalize_text(text)
    idx = Indexer()
    batch_texts = []
    batch_metas = []
    total = 0
    for i, ch in enumerate(chunk_text(norm, chunk_size=1200, overlap=200)):
        batch_texts.append(ch)
        batch_metas.append({"source": p.name, "chunk_id": i, "text": ch})
        total += 1
        if len(batch_texts) >= 32:
            idx.add_batch(batch_texts, batch_metas, batch_size=8)
            batch_texts = []
            batch_metas = []
    if batch_texts:
        idx.add_batch(batch_texts, batch_metas, batch_size=8)
    idx.save(out_dir)
    print(f"Indexed {total} chunks from {p.name} into {out_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--out', default='indexed_single')
    args = parser.parse_args()
    build_single(args.pdf, args.out)
