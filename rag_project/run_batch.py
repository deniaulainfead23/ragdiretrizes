"""Executa perguntas estruturadas de `questions/questions.yaml` e salva respostas JSONL.
Uso:
    python run_batch.py --index indexed --out responses.jsonl --openai_key YOUR_KEY
Se `openai_key` for omitida, salva o fallback (snippets) em JSON.
"""
import argparse
import json

from dotenv import load_dotenv

from openai_vector_store import cloud_rag_query
from rag_project.question_catalog import get_questions
from rag_project.corpus_registry import load_registry, registered_documents
from rag.query import get_cached_answer, rag_query, save_cached_answer
from rag_project.vector_backend import resolve_backend


def main(index_folder: str, out_file: str, openai_key: str = None, vector_store_id: str = None, backend: str | None = None):
    load_dotenv()
    openai_key = openai_key or __import__('os').environ.get('OPENAI_API_KEY')
    resolved_backend = resolve_backend(backend, openai_key)
    out = []
    registry = load_registry()
    questions = [q for q in get_questions() if q.get('question_type') == 'evidence_retrieval']
    for q in questions:
        question_id = q['question_id']
        text = q['question_text']
        print('Query:', question_id, text)
        for country_entry, documents in _countries_and_documents(registry, q.get('target_country')):
            country = country_entry['country']
            document_ids = [document['document_id'] for document in documents]
            cache_index = f'vector_store:{vector_store_id}' if vector_store_id else index_folder
            resp = get_cached_answer(cache_index, text, question_id=question_id, country=country, top_k=10) if vector_store_id else None
            if resp is None:
                if vector_store_id and resolved_backend == 'openai':
                    resp = cloud_rag_query(vector_store_id, text, openai_key)
                    save_cached_answer(cache_index, text, resp, question_id=question_id, country=country, top_k=10)
                else:
                    resp = rag_query(index_folder, text, question_id, country, q['framework'], q['category_id'], document_ids, top_k=10, openai_api_key=openai_key, question_version=str(q['version']))
            out_obj = {'question_id': question_id, 'country': country, 'response': resp, 'evidence_ids': [], 'validation_status': 'candidate'}
            out.append(out_obj)
    with open(out_file, 'w', encoding='utf-8') as f:
        for obj in out:
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')
    print('Saved responses to', out_file)


def _countries_and_documents(registry: dict, target_country: str | None):
    grouped = {}
    for entry, document in registered_documents(registry, target_country):
        grouped.setdefault(entry['country'], (entry, []))[1].append(document)
    return grouped.values()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', default='indexed', help='Pasta do índice salvo')
    parser.add_argument('--out', default='responses.jsonl', help='Arquivo de saída')
    parser.add_argument('--openai_key', default=None, help='Chave OpenAI (opcional)')
    parser.add_argument('--vector_store_id', default=None, help='Consulta o Vector Store hospedado em vez do FAISS local')
    parser.add_argument('--backend', default=None, choices=['openai', 'local'], help='Backend vetorial: openai ou local')
    args = parser.parse_args()
    main(args.index, args.out, args.openai_key, args.vector_store_id, args.backend)
