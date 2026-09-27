import hashlib
import json
import os
from pathlib import Path

from openai import OpenAI

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
    candidates = []
    for hit in hits:
        metadata = hit['metadata']
        candidates.append({
            'document_id': metadata.get('document_id', ''),
            'document_title': metadata.get('title', ''),
            'source_path': metadata.get('source') or metadata.get('path', ''),
            'page_start': metadata.get('page_start') or metadata.get('page', ''),
            'page_end': metadata.get('page_end') or metadata.get('page', ''),
            'chunk_id': metadata.get('chunk_id', ''),
            'source_language': metadata.get('language', ''),
            'translation_status': metadata.get('translation_status', ''),
            'semantic_score': hit.get('score', ''),
            'source_text': str(metadata.get('source_text') or metadata.get('text', ''))[:1500],
            'translated_text_en': str(metadata.get('translated_text_en', ''))[:1500],
        })
    context = json.dumps(candidates, ensure_ascii=False)
    prompt = f"""Responda à pergunta somente usando os trechos candidatos fornecidos. Não use conhecimento externo.
Retorne somente JSON válido com as chaves question_id, country, response, evidences e validation_status.
Cada item em evidences deve conter document_id, document_title, page_start, page_end, chunk_id,
source_language, source_text, translated_text_en, translated_text_pt, translation_status, semantic_score,
evidence_classification e validation_status.
Use somente candidatos fornecidos. Copie document_id, título, páginas, chunk_id, idioma e semantic_score
exatamente do candidato. source_text deve reproduzir literalmente o texto de origem fornecido, sem paráfrase.
translated_text_en é a tradução usada para recuperação; use-a como apoio semântico, nunca como citação original.
Traduza apenas source_text para português se source_language estiver preenchido e não for português;
use translation_status='translated'. Para português, repita o trecho e use 'not_needed'. Se o idioma
estiver vazio ou não puder ser identificado pelo candidato, não adivinhe: deixe a tradução vazia e use
'not_provided'. Deixe evidence_classification vazio para revisão humana. Não use validation_status='validated'.
Use 'candidate' quando uma evidência apoiar a resposta e 'inconclusive' se não houver apoio suficiente.

question_id: {question_id}
country: {country}
framework: {framework}
category_id: {category_id}
pergunta: {question}
trechos candidatos: {context}

JSON:"""

    cached = get_cached_answer(index_folder, question, top_k=top_k, question_id=question_id, country=country, question_version=question_version)
    if cached is not None:
        print('[3/4] Resposta recuperada do cache.')
        print('[4/4] Gerando resposta...')
        return cached

    if openai_api_key:
        print('[4/4] Gerando resposta com OpenAI...')
        client = OpenAI(api_key=openai_api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.0,
        )
        answer = resp.choices[0].message.content or ""
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
