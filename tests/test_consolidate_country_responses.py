import csv
import json

from rag_project.consolidate_country_responses import consolidate
from rag_project.repair_official_run import repair


def test_consolidate_preserves_original_excerpt(tmp_path):
    input_dir = tmp_path / 'countries' / 'brasil'
    input_dir.mkdir(parents=True)
    response = {
        'response': 'Resposta com evidencia.',
        'evidence_ids': [
            {
                'document_id': 'BR-01',
                'document': 'curriculo.pdf',
                'page': 12,
                'original_excerpt': 'Trecho original recuperado.',
                'classification': 'curricular',
                'validation_status': 'candidate',
            }
        ],
    }
    with (input_dir / 'respostas.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['country', 'question_id', 'response'])
        writer.writeheader()
        writer.writerow({'country': 'brasil', 'question_id': 'Q01', 'response': json.dumps(response)})

    _, evidence_path = consolidate(input_dir.parent, tmp_path / 'consolidado')

    with evidence_path.open('r', encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]['original_text'] == 'Trecho original recuperado.'


def test_repair_flags_empty_embedded_response_with_existing_evidence(tmp_path):
    run_dir = tmp_path / 'official_run' / 'brasil'
    run_dir.mkdir(parents=True)
    payload = {
        'question_id': 'Q04',
        'country': 'brasil',
        'response': '',
        'evidences': [{'document_id': 'BR_003', 'source_text': 'Trecho recuperado.'}],
    }
    with (run_dir / 'respostas.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['question_id', 'response', 'validation_status', 'review_notes'])
        writer.writeheader()
        writer.writerow({
            'question_id': 'Q04',
            'response': json.dumps(payload),
            'validation_status': 'candidate',
            'review_notes': '',
        })
    with (run_dir / 'evidencias.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['question_id', 'document_id', 'page_start', 'source_text'])
        writer.writeheader()
        writer.writerow({'question_id': 'Q04', 'document_id': 'BR_003', 'page_start': '15', 'source_text': 'Trecho recuperado.'})

    content_path = tmp_path / 'conteudos.jsonl'
    content_path.write_text('', encoding='utf-8')
    repair(run_dir.parent, content_path)

    with (run_dir / 'respostas.csv').open('r', encoding='utf-8-sig', newline='') as handle:
        row = next(csv.DictReader(handle))

    assert row['response'] == ''
    assert row['validation_status'] == 'inconclusive'
    assert 'embedded_json_response_empty' in row['review_notes']