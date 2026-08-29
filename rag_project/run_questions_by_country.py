from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rag_project.question_catalog import get_questions


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


def run_question_plan(country: str, output_dir: str | Path) -> list[dict]:
    plan = build_country_question_plan(country)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_entries = []
    for item in plan:
        run_entries.append({
            'run_id': f"{country}-{item['question_id']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            'question_id': item['question_id'],
            'country': country,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'framework': item['framework'],
            'category_id': item['category_id'],
            'question_version': item['version'],
            'status': 'planned',
            'number_of_hits': 0,
        })

    out_path = out_dir / 'question_run_log.csv'
    with out_path.open('w', encoding='utf-8', newline='') as handle:
        handle.write('run_id,question_id,country,timestamp,framework,category_id,question_version,status,number_of_hits\n')
        for row in run_entries:
            handle.write(','.join([
                row['run_id'], row['question_id'], row['country'], row['timestamp'], row['framework'], row['category_id'], row['question_version'], row['status'], str(row['number_of_hits'])
            ]) + '\n')

    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description='Executa o plano de perguntas por país, em versão estruturada e compatível com o legado.')
    parser.add_argument('--country', required=True, help='País para executar as perguntas de recuperação documental')
    parser.add_argument('--out', default='analysis/questions', help='Diretório de saída dos logs de execução')
    args = parser.parse_args()

    plan = run_question_plan(args.country, args.out)
    print(json.dumps({'country': args.country, 'questions': len(plan), 'output_dir': str(Path(args.out))}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
