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


def _cache_key(index_folder: str, question: str, top_k: int, question_id: str = "", country: str = "", corpus_version: str = "3.0", question_version: str = "2.0") -> str:
    payload = f"v{corpus_version}|questions-v{question_version}|{index_folder}|{country}|{question_id}|{question.strip()}|{top_k}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_cached_answer(index_folder: str, question: str, top_k: int = 5, question_id: str = "", country: str = "", question_version: str = "2.0"):
    cache = _read_cache()
    key = _cache_key(index_folder, question, top_k, question_id, country, question_version=question_version)
    item = cache.get(key)
    if not item:
        return None
    return item.get("answer")


def save_cached_answer(index_folder: str, question: str, answer: str, top_k: int = 5, question_id: str = "", country: str = "", question_version: str = "2.0"):
    cache = _read_cache()
    key = _cache_key(index_folder, question, top_k, question_id, country, question_version=question_version)
    cache[key] = {
        "question": question,
        "index_folder": index_folder,
        "top_k": top_k,
        "answer": answer,
    }
    _write_cache(cache)
    return answer


def rag_query(index_folder: str, question: str, question_id: str = "", country: str = "", framework: str = "", category_id: str = "", document_ids: list[str] | None = None, top_k: int = 10, openai_api_key: str = None, question_version: str = "2.0"):
    print('[1/4] Recebendo pergunta...')
    print(f'[2/4] Carregando índice local em {index_folder}...')
    idx = Indexer()
    idx.load(index_folder)
    print(f'[2/4] Índice carregado. Buscando {top_k} trechos relevantes...')
    hits = idx.query(question, top_k=top_k, country=country, document_ids=set(document_ids or []))
    snippets = [h['metadata'] for h in hits]
    print(f'[3/4] Encontrados {len(snippets)} trechos relevantes.')
    context = "\n\n---\n\n".join([f"Source: {s.get('source')}\nText:\n{s.get('text')[:1000]}" for s in snippets])
    prompt = f"""Responda somente com base nas evidências abaixo. Preserve incertezas e não invente dados.
Retorne JSON com: question_id, country, response, evidence_ids, evidence_classification, validation_status.
Cada evidência deve registrar document_id, documento/source, página, trecho original, classificação e validation_status.
question_id: {question_id}
country: {country}
framework: {framework}
category_id: {category_id}

EVIDÊNCIAS:
{context}

PERGUNTA: {question}

RESPOSTA JSON:"""

    cached = get_cached_answer(index_folder, question, top_k=top_k, question_id=question_id, country=country, question_version=question_version)
    if cached is not None:
        print('[3/4] Resposta recuperada do cache.')
        print('[4/4] Gerando resposta...')
        return cached

    if openai_api_key:
        print('[4/4] Gerando resposta com OpenAI...')
        openai.api_key = openai_api_key
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.0,
        )
        answer = resp['choices'][0]['message']['content']
        save_cached_answer(index_folder, question, answer, top_k=top_k, question_id=question_id, country=country, question_version=question_version)
        return answer

    out = {
        "question": question,
        "retrieved": snippets,
        "prompt": prompt[:4000],
        "cache_status": "miss"
    }
    print('[4/4] Gerando resposta local fallback...')
    return json.dumps(out, ensure_ascii=False, indent=2)
