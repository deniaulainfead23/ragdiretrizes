"""Upload e consultas RAG usando Vector Stores hospedados pela OpenAI."""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from rag_project.vector_backend import write_vector_backend_manifest


DEFAULT_MODEL = 'gpt-4o-mini'
MANIFEST_PATH = Path(__file__).resolve().parent / '.openai_vector_stores.json'


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


def sync_dataset(file_path: str, dataset_name: str, existing_id: str | None = None, api_key: str | None = None) -> str:
    manifest = {}
    if MANIFEST_PATH.exists():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            manifest = {}

    vector_store_id = existing_id or manifest.get(dataset_name, {}).get('vector_store_id')
    if not vector_store_id:
        vector_store_id = upload_dataset(file_path, f'ragdiretrizes-{dataset_name}', api_key)

    manifest[dataset_name] = {
        'vector_store_id': vector_store_id,
        'file': str(Path(file_path)),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    write_vector_backend_manifest({
        'backend': 'openai',
        'vector_store_id': vector_store_id,
        'model': DEFAULT_MODEL,
        'index_folder': str(Path(file_path).parent),
        'updated_at': __import__('datetime').datetime.utcnow().isoformat(timespec='seconds') + 'Z',
    })
    print(f'{dataset_name}: vector_store_id={vector_store_id}')
    print(f'Manifesto local: {MANIFEST_PATH}')
    return vector_store_id


def cloud_rag_query(vector_store_id: str, question: str, api_key: str | None = None, model: str = DEFAULT_MODEL, question_id: str = "", country: str = "", framework: str = "", category_id: str = "") -> str:
    print('[1/4] Recebendo pergunta...')
    print(f'[2/4] Buscando documentos no Vector Store {vector_store_id}...')
    client = OpenAI(api_key=api_key or os.environ.get('OPENAI_API_KEY'))
    response = client.responses.create(
        model=model,
        input=(f'''Responda em português usando somente as evidências recuperadas.
    Retorne JSON com: question_id, country, response, evidence_ids, evidence_classification, validation_status.
    Para cada evidência, informe document_id, documento, página, trecho original, classificação e validation_status.
    question_id: {question_id}
    country: {country}
    framework: {framework}
    category_id: {category_id}
    Pergunta: {question}'''),
        tools=[{
            'type': 'file_search',
            'vector_store_ids': [vector_store_id],
            'max_num_results': 8,
            'filters': {'type': 'eq', 'key': 'country', 'value': country} if country else None,
        }],
    )
    print('[3/4] Encontrados trechos relevantes para a consulta.')
    print('[4/4] Gerando resposta...')
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
    sync_parser = subparsers.add_parser('sync', help='Hospeda os datasets e reutiliza IDs já registrados')
    sync_parser.add_argument('--original', default='../corpus/dataset_output/dataset_original.jsonl')
    sync_parser.add_argument('--english', default='../corpus/dataset_output/dataset_english.jsonl')
    sync_parser.add_argument('--english-vector-store-id', default=None, help='ID inglês já criado anteriormente')
    sync_parser.add_argument('--openai_key', default=None)
    args = parser.parse_args()

    if args.command == 'upload':
        upload_dataset(args.file, args.name, args.openai_key)
    elif args.command == 'query':
        print(cloud_rag_query(args.vector_store_id, args.question, args.openai_key))
    else:
        sync_dataset(args.original, 'original', api_key=args.openai_key)
        sync_dataset(args.english, 'english', existing_id=args.english_vector_store_id, api_key=args.openai_key)


if __name__ == '__main__':
    main()
