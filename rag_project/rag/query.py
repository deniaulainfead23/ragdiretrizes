import hashlib
import json
import os
from pathlib import Path

import openai

from .indexer import Indexer

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"
CACHE_FILE = CACHE_DIR / "openai_cache.json"


def _ensure_cache_file():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_FILE.exists():
        CACHE_FILE.write_text("{}", encoding="utf-8")
    return CACHE_FILE


def _read_cache():
    try:
        with open(_ensure_cache_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_cache(cache):
    with open(_ensure_cache_file(), "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _cache_key(index_folder: str, question: str, top_k: int) -> str:
    payload = f"{index_folder}|{question.strip()}|{top_k}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_cached_answer(index_folder: str, question: str, top_k: int = 5):
    cache = _read_cache()
    key = _cache_key(index_folder, question, top_k)
    item = cache.get(key)
    if not item:
        return None
    return item.get("answer")


def save_cached_answer(index_folder: str, question: str, answer: str, top_k: int = 5):
    cache = _read_cache()
    key = _cache_key(index_folder, question, top_k)
    cache[key] = {
        "question": question,
        "index_folder": index_folder,
        "top_k": top_k,
        "answer": answer,
    }
    _write_cache(cache)
    return answer


def rag_query(index_folder: str, question: str, top_k: int = 5, openai_api_key: str = None):
    idx = Indexer()
    idx.load(index_folder)
    hits = idx.query(question, top_k=top_k)
    snippets = [h['metadata'] for h in hits]
    context = "\n\n---\n\n".join([f"Source: {s.get('source')}\nText:\n{s.get('text')[:1000]}" for s in snippets])
    prompt = f"Responda a pergunta usando apenas as evidências listadas abaixo. Retorne uma síntese curta e liste as fontes utilizadas.\n\nEVIDÊNCIAS:\n{context}\n\nPERGUNTA: {question}\n\nRESPOSTA:"

    cached = get_cached_answer(index_folder, question, top_k=top_k)
    if cached is not None:
        return cached

    if openai_api_key:
        openai.api_key = openai_api_key
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.0,
        )
        answer = resp['choices'][0]['message']['content']
        save_cached_answer(index_folder, question, answer, top_k=top_k)
        return answer

    out = {
        "question": question,
        "retrieved": snippets,
        "prompt": prompt[:4000],
        "cache_status": "miss"
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
