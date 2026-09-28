import json
from types import SimpleNamespace

from rag_project.openai_vector_store import _upload_jsonl_by_country


def test_jsonl_upload_preserves_unicode_line_separators(tmp_path):
    dataset = tmp_path / 'pages.jsonl'
    records = [
        {'country': 'brasil', 'source_text': 'trecho\u2028continua'},
        {'country': 'estonia', 'source_text': 'teine lehekülg'},
    ]
    dataset.write_text(
        ''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records),
        encoding='utf-8',
    )

    uploaded_records = {}

    class FakeFiles:
        def upload_and_poll(self, vector_store_id, file, attributes):
            filename, content = file
            lines = content.getvalue().decode('utf-8').split('\n')
            uploaded_records[attributes['country']] = [
                json.loads(line) for line in lines if line.strip()
            ]
            return SimpleNamespace(status='completed', id=filename)

    client = SimpleNamespace(
        vector_stores=SimpleNamespace(files=FakeFiles()),
    )

    _upload_jsonl_by_country(client, 'vs-test', dataset)

    assert uploaded_records == {
        'brasil': [records[0]],
        'estonia': [records[1]],
    }