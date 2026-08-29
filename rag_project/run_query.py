"""Script para consultar o índice e (opcionalmente) usar uma API de LLM para sintetizar respostas."""
import argparse
import os
from rag.query import rag_query
from openai_vector_store import cloud_rag_query
from dotenv import load_dotenv

def main(index_folder: str, question: str, openai_key: str = None, vector_store_id: str = None):
    if openai_key is None:
        load_dotenv()
        openai_key = os.environ.get('OPENAI_API_KEY')
    if vector_store_id:
        out = cloud_rag_query(vector_store_id, question, openai_key)
    else:
        out = rag_query(index_folder, question, top_k=5, openai_api_key=openai_key)
    print(out)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', default='indexed', help='Pasta do índice salvo')
    parser.add_argument('--question', required=True, help='Pergunta a ser consultada')
    parser.add_argument('--openai_key', default=None, help='Chave OpenAI (opcional)')
    parser.add_argument('--vector_store_id', default=None, help='ID do Vector Store hospedado na OpenAI')
    args = parser.parse_args()
    main(args.index, args.question, args.openai_key, args.vector_store_id)
