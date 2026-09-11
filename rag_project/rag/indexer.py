import json
import hashlib
import os
import re
from typing import Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


class Indexer:
    def __init__(self, model_name: str = MODEL_NAME, dim: int = 384):
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        try:
            import torch

            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
        except (ImportError, RuntimeError):
            pass
        self.model = None
        self.dim = dim
        try:
            self.model = SentenceTransformer(model_name, local_files_only=True)
            dimension_method = getattr(self.model, "get_embedding_dimension", None)
            if dimension_method is None:
                dimension_method = self.model.get_sentence_embedding_dimension
            self.dim = dimension_method()
        except Exception:
            self.model = None
        self.index = faiss.IndexFlatIP(self.dim)
        self.metadatas: List[Dict] = []

    def _encode(self, texts: List[str]) -> np.ndarray:
        if self.model is not None:
            return np.asarray(
                self.model.encode(
                    texts,
                    batch_size=min(8, len(texts)),
                    show_progress_bar=False,
                    convert_to_numpy=True,
                ),
                dtype=np.float32,
            )

        embeddings = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % self.dim
                sign = 1.0 if digest[4] & 1 else -1.0
                embeddings[row, index] += sign
        return embeddings

    def add(self, texts: List[str], metadatas: List[Dict]):
        self.add_batch(texts, metadatas)

    def add_batch(self, texts: List[str], metadatas: List[Dict], batch_size: int = 8):
        if not texts:
            return
        n = len(texts)
        for i in range(0, n, batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            emb = self._encode(batch_texts)
            if emb.ndim == 1:
                emb = emb.reshape(1, -1)
            faiss.normalize_L2(emb)
            self.index.add(emb)
            self.metadatas.extend(batch_meta)

    def validate_alignment(self) -> bool:
        return self.index.ntotal == len(self.metadatas)

    def save(self, folder: str):
        os.makedirs(folder, exist_ok=True)
        faiss.write_index(self.index, os.path.join(folder, "index.faiss"))
        with open(os.path.join(folder, "metadatas.json"), "w", encoding="utf-8") as f:
            json.dump(self.metadatas, f, ensure_ascii=False)

    def load(self, folder: str):
        index_path = os.path.join(folder, "index.faiss")
        meta_path = os.path.join(folder, "metadatas.json")
        if not os.path.exists(index_path) or not os.path.exists(meta_path):
            raise FileNotFoundError(f"Índice ou metadados não encontrados em {folder}")
        self.index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            self.metadatas = json.load(f)

    def query(self, query_text: str, top_k: int = 5, country: str | None = None, document_ids: set[str] | None = None):
        if self.index.ntotal == 0:
            return []
        q_emb = self._encode([query_text])
        faiss.normalize_L2(q_emb)
        scores, ids = self.index.search(q_emb, self.index.ntotal)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0 or idx >= len(self.metadatas):
                continue
            meta = self.metadatas[idx]
            if country and str(meta.get("country", "")).strip().lower() != country.strip().lower():
                continue
            if document_ids and meta.get("document_id") not in document_ids:
                continue
            results.append({"score": float(score), "metadata": meta})
            if len(results) >= top_k:
                break
        return results
