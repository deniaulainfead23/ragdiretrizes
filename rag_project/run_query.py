"""Script para consultar o índice e (opcionalmente) usar uma API de LLM para sintetizar respostas."""
import argparse
import os
from rag.query import rag_query
from dotenv import load_dotenv

def main(index_folder: str, question: str, openai_key: str = None):
    if openai_key is None:
        load_dotenv()
        openai_key = os.environ.get('OPENAI_API_KEY')
    out = rag_query(index_folder, question, top_k=5, openai_api_key=openai_key)
    print(out)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', default='indexed', help='Pasta do índice salvo')
    parser.add_argument('--question', required=True, help='Pergunta a ser consultada')
    parser.add_argument('--openai_key', default=None, help='Chave OpenAI (opcional)')
    args = parser.parse_args()
    main(args.index, args.question, args.openai_key)
