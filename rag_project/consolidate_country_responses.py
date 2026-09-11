from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _parse_response(value: str) -> dict:
    text = (value or '').strip()
    if text.startswith('```'):
        lines = text.splitlines()
        text = '\n'.join(lines[1:-1]) if len(lines) >= 3 else ''
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def consolidate(input_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    response_rows: list[dict] = []
    evidence_rows: list[dict] = []

    for source in sorted(input_dir.glob('*/respostas.csv')):
        with source.open('r', encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                parsed = _parse_response(row.get('response', ''))
                country = row.get('country', source.parent.name)
                question_id = row.get('question_id', '')
                evidence = parsed.get('evidence_ids', [])
                if not isinstance(evidence, list):
                    evidence = []
                response_rows.append({
                    'country': country,
                    'question_id': question_id,
                    'question_text': row.get('question_text', ''),
                    'response': parsed.get('response', row.get('response', '')),
                    'situacao_resposta': row.get('validation_status', parsed.get('validation_status', 'candidate')),
                    'evidence_count': len(evidence),
                    'evidence_classification': parsed.get('evidence_classification', ''),
                    'validation_status': row.get('validation_status', parsed.get('validation_status', 'candidate')),
                    'source_file': source.as_posix(),
                })
                for number, item in enumerate(evidence, start=1):
                    if not isinstance(item, dict):
                        continue
                    evidence_rows.append({
                        'country': country,
                        'question_id': question_id,
                        'evidence_number': number,
                        'document_id': item.get('document_id', ''),
                        'document': item.get('document', ''),
                        'page': item.get('page', item.get('página', '')),
                        'original_text': item.get(
                            'original_text',
                            item.get('original_excerpt', item.get('trecho_original', '')),
                        ),
                        'classification': item.get('classification', item.get('classificação', '')),
                        'evidence_validation_status': item.get('validation_status', ''),
                    })

    output_dir.mkdir(parents=True, exist_ok=True)
    responses_path = output_dir / 'respostas_consolidadas.csv'
    evidence_path = output_dir / 'evidencias_consolidadas.csv'
    response_fields = list(response_rows[0]) if response_rows else ['country', 'question_id']
    evidence_fields = list(evidence_rows[0]) if evidence_rows else ['country', 'question_id']
    for path, rows, fields in ((responses_path, response_rows, response_fields), (evidence_path, evidence_rows, evidence_fields)):
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    return responses_path, evidence_path


def main() -> None:
    parser = argparse.ArgumentParser(description='Consolida respostas RAG por país e pergunta.')
    parser.add_argument('--input', default='analysis/countries')
    parser.add_argument('--output', default='analysis/consolidado')
    args = parser.parse_args()
    responses_path, evidence_path = consolidate(Path(args.input), Path(args.output))
    print(f'responses={responses_path}')
    print(f'evidence={evidence_path}')


if __name__ == '__main__':
    main()