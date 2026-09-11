import csv
import json

from rag_project.consolidate_country_responses import consolidate


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