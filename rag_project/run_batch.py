"""Leia `questions.txt` (uma pergunta por linha), consulta o índice e salva cada resposta em `responses.jsonl`.
Uso:
    python run_batch.py --index indexed --questions questions.txt --out responses.jsonl --openai_key YOUR_KEY
Se `openai_key` for omitida, salva o fallback (snippets) em JSON.
"""
import argparse
import json
import os
from dotenv import load_dotenv
from openai_vector_store import cloud_rag_query
from rag.query import get_cached_answer, rag_query, save_cached_answer

def main(index_folder: str, questions_file: str, out_file: str, openai_key: str = None, vector_store_id: str = None):
    load_dotenv()
    openai_key = openai_key or os.environ.get('OPENAI_API_KEY')
    out = []
    with open(questions_file, 'r', encoding='utf-8') as f:
        questions = [l.strip() for l in f if l.strip()]
    for q in questions:
        print('Query:', q)
        cache_index = f'vector_store:{vector_store_id}' if vector_store_id else index_folder
        resp = get_cached_answer(cache_index, q) if vector_store_id else None
        if resp is None:
            resp = cloud_rag_query(vector_store_id, q, openai_key) if vector_store_id else rag_query(index_folder, q, top_k=5, openai_api_key=openai_key)
            if vector_store_id:
                save_cached_answer(cache_index, q, resp)
        # if resp is a string (LLM answer) keep as is; if JSON (fallback) already string
        out_obj = {'question': q, 'response': resp}
        out.append(out_obj)
    with open(out_file, 'w', encoding='utf-8') as f:
        for obj in out:
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')
    print('Saved responses to', out_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', default='indexed', help='Pasta do índice salvo')
    parser.add_argument('--questions', required=True, help='Arquivo de perguntas (uma por linha)')
    parser.add_argument('--out', default='responses.jsonl', help='Arquivo de saída')
    parser.add_argument('--openai_key', default=None, help='Chave OpenAI (opcional)')
    parser.add_argument('--vector_store_id', default=None, help='Consulta o Vector Store hospedado em vez do FAISS local')
    args = parser.parse_args()
    main(args.index, args.questions, args.out, args.openai_key, args.vector_store_id)
