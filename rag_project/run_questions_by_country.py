from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from rag_project.question_catalog import get_questions
from rag_project.corpus_registry import get_country, load_registry, registered_documents
from rag_project.rag.query import rag_query


def build_country_question_plan(country: str) -> list[dict]:
    questions = get_questions()
    selected = []
    for q in questions:
        if q.get('question_type') != 'evidence_retrieval':
            continue
        if q.get('target_country') in {None, country, country.lower()}:
            selected.append({
                'question_id': q['question_id'],
                'title': q['title'],
                'question_text': q['question_text'],
                'target_country': q.get('target_country') or country,
                'question_type': q['question_type'],
                'analysis_stage': q['analysis_stage'],
                'framework': q['framework'],
                'category_id': q['category_id'],
                'version': q['version'],
            })
    return selected


def run_question_plan(country: str, output_dir: str | Path, index_folder: str = 'indexed', openai_api_key: str | None = None) -> list[dict]:
    plan = build_country_question_plan(country)
    registry = load_registry()
    country_entry = get_country(registry, country)
    if not country_entry or not country_entry.get('include_in_analysis'):
        raise ValueError(f'País não está ativo no registro: {country}')
    documents = list(registered_documents(registry, country))
    document_ids = [document['document_id'] for _, document in documents]
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_entries = []
    response_rows = []
    for item in plan:
        response = rag_query(index_folder, item['question_text'], item['question_id'], country, item['framework'], item['category_id'], document_ids, top_k=10, openai_api_key=openai_api_key, question_version=str(item['version']))
        parsed_response = _parse_response(response)
        response_rows.append({'question_id': item['question_id'], 'question_text': item['question_text'], 'country': country, 'response': response, 'evidence_ids': '; '.join(parsed_response.get('evidence_ids', [])), 'validation_status': parsed_response.get('validation_status', 'candidate')})
        run_entries.append({
            'run_id': f"{country}-{item['question_id']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            'question_id': item['question_id'],
            'country': country,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'framework': item['framework'],
            'category_id': item['category_id'],
            'question_version': item['version'],
            'status': 'executed',
            'number_of_hits': response.count('document_id') if isinstance(response, str) else 0,
        })

    out_path = out_dir / 'question_run_log.csv'
    with out_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=run_entries[0].keys() if run_entries else ['question_id'])
        writer.writeheader()
        writer.writerows(run_entries)

    responses_path = out_dir / 'respostas.csv'
    with responses_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=response_rows[0].keys() if response_rows else ['question_id'])
        writer.writeheader()
        writer.writerows(response_rows)

    return plan


def _parse_response(response: str) -> dict:
    try:
        value = json.loads(response)
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description='Executa o plano de perguntas por país, em versão estruturada e compatível com o legado.')
    parser.add_argument('--country', required=True, help='País para executar as perguntas de recuperação documental')
    parser.add_argument('--out', default=None, help='Diretório de saída; padrão analysis/countries/<country>')
    parser.add_argument('--index', default='indexed', help='Pasta do índice versionado')
    parser.add_argument('--openai_key', default=None, help='Chave OpenAI opcional')
    args = parser.parse_args()

    output_dir = args.out or str(Path('analysis') / 'countries' / args.country)
    plan = run_question_plan(args.country, output_dir, args.index, args.openai_key)
    print(json.dumps({'country': args.country, 'questions': len(plan), 'output_dir': str(Path(args.out))}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
