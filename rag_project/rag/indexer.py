import json
import os
from typing import Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


class Indexer:
    def __init__(self, model_name: str = MODEL_NAME, dim: int = 384):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dim)
        self.metadatas: List[Dict] = []

    def add(self, texts: List[str], metadatas: List[Dict]):
        self.add_batch(texts, metadatas)

    def add_batch(self, texts: List[str], metadatas: List[Dict], batch_size: int = 8):
        if not texts:
            return
        n = len(texts)
        for i in range(0, n, batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            emb = self.model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True)
            emb = np.asarray(emb, dtype=np.float32)
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

    def query(self, query_text: str, top_k: int = 5):
        if self.index.ntotal == 0:
            return []
        q_emb = self.model.encode([query_text], convert_to_numpy=True)
        q_emb = np.asarray(q_emb, dtype=np.float32)
        faiss.normalize_L2(q_emb)
        scores, ids = self.index.search(q_emb, min(top_k, self.index.ntotal))
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0 or idx >= len(self.metadatas):
                continue
            meta = self.metadatas[idx]
            results.append({"score": float(score), "metadata": meta})
        return results
