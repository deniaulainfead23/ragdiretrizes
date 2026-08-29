"""Upload e consultas RAG usando Vector Stores hospedados pela OpenAI."""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_MODEL = 'gpt-4o-mini'


def upload_dataset(file_path: str, vector_store_name: str, api_key: str | None = None) -> str:
    client = OpenAI(api_key=api_key or os.environ.get('OPENAI_API_KEY'))
    vector_store = client.vector_stores.create(name=vector_store_name)
    with open(file_path, 'rb') as handle:
        upload_name = Path(file_path).name
        if Path(file_path).suffix.lower() == '.jsonl':
            upload_name = f'{Path(file_path).stem}.txt'
        uploaded = client.vector_stores.files.upload_and_poll(
            vector_store_id=vector_store.id,
            file=(upload_name, handle),
        )
    if uploaded.status != 'completed':
        raise RuntimeError(f'Falha ao indexar arquivo: {uploaded.status}')
    print(f'Arquivo indexado: {uploaded.id}')
    print(f'vector_store_id={vector_store.id}')
    return vector_store.id


def cloud_rag_query(vector_store_id: str, question: str, api_key: str | None = None, model: str = DEFAULT_MODEL) -> str:
    client = OpenAI(api_key=api_key or os.environ.get('OPENAI_API_KEY'))
    response = client.responses.create(
        model=model,
        input=(
            'Responda em português usando somente as evidências recuperadas no corpus. '
            'Faça uma síntese curta e informe as fontes quando estiverem disponíveis.\n\n'
            f'Pergunta: {question}'
        ),
        tools=[{
            'type': 'file_search',
            'vector_store_ids': [vector_store_id],
            'max_num_results': 8,
        }],
    )
    return response.output_text


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description='Hospeda o dataset na OpenAI e consulta com File Search.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    upload_parser = subparsers.add_parser('upload', help='Cria um Vector Store e indexa um arquivo')
    upload_parser.add_argument('--file', required=True, help='Dataset JSONL ou documento para indexar')
    upload_parser.add_argument('--name', default='ragdiretrizes-corpus', help='Nome do Vector Store')
    upload_parser.add_argument('--openai_key', default=None)

    query_parser = subparsers.add_parser('query', help='Consulta um Vector Store com File Search')
    query_parser.add_argument('--vector_store_id', required=True)
    query_parser.add_argument('--question', required=True)
    query_parser.add_argument('--openai_key', default=None)
    args = parser.parse_args()

    if args.command == 'upload':
        upload_dataset(args.file, args.name, args.openai_key)
    else:
        print(cloud_rag_query(args.vector_store_id, args.question, args.openai_key))


if __name__ == '__main__':
    main()
