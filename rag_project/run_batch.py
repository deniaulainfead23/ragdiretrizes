"""Leia `questions.txt` (uma pergunta por linha), consulta o índice e salva cada resposta em `responses.jsonl`.
Uso:
    python run_batch.py --index indexed --questions questions.txt --out responses.jsonl --openai_key YOUR_KEY
Se `openai_key` for omitida, salva o fallback (snippets) em JSON.
"""
import argparse
import json
from rag.query import rag_query

def main(index_folder: str, questions_file: str, out_file: str, openai_key: str = None):
    out = []
    with open(questions_file, 'r', encoding='utf-8') as f:
        questions = [l.strip() for l in f if l.strip()]
    for q in questions:
        print('Query:', q)
        resp = rag_query(index_folder, q, top_k=5, openai_api_key=openai_key)
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
    args = parser.parse_args()
    main(args.index, args.questions, args.out, args.openai_key)
