import csv
import json
from pathlib import Path
from types import SimpleNamespace

from rag_project import build_content_dataset
from rag_project import build_index


def test_page_dataset_records_selection_and_exclusion_report(tmp_path, monkeypatch):
    processed_root = tmp_path / 'dados_intermediarios' / 'processed'
    verified_text = processed_root / 'brasil' / 'verified.md'
    verified_text.parent.mkdir(parents=True)
    verified_text.write_text('## PAGE 8\nEvidence from the official curriculum.', encoding='utf-8')

    documents_path = tmp_path / 'documentos.csv'
    with documents_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            'document_id', 'country', 'country_code', 'source_scope', 'framework_source',
            'title', 'year', 'language', 'audit_group', 'source_path',
            'validation_status', 'document_role',
        ])
        writer.writeheader()
        writer.writerows([
            {
                'document_id': 'BR-01', 'country': 'Brasil', 'country_code': 'BR',
                'source_scope': 'national', 'framework_source': '', 'title': 'Currículo BR',
                'year': '2024', 'language': 'pt', 'audit_group': 'A',
                'source_path': 'brasil/verified.pdf', 'validation_status': 'validated',
                'document_role': 'primary',
            },
            {
                'document_id': 'BR-02', 'country': 'Brasil', 'country_code': 'BR',
                'source_scope': 'national', 'framework_source': '', 'title': 'Pendente',
                'year': '2025', 'language': 'pt', 'audit_group': 'A',
                'source_path': 'brasil/pending.pdf', 'validation_status': 'pending_review',
                'document_role': 'complementary',
            },
            {
                'document_id': 'DLGF-18', 'country': '', 'country_code': '',
                'source_scope': 'international_reference', 'framework_source': 'DLGF_2018',
                'title': 'DLGF', 'year': '2018', 'language': 'en', 'audit_group': 'A',
                'source_path': 'Unesco/dlgf.pdf', 'validation_status': 'validated',
                'document_role': 'reference',
            },
        ])

    processed_path = tmp_path / 'processed_documents.csv'
    with processed_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['document_id', 'status', 'processed_path'])
        writer.writeheader()
        writer.writerows([
            {'document_id': 'BR-01', 'status': 'ready', 'processed_path': 'dados_intermediarios/processed/brasil/verified.md'},
            {'document_id': 'BR-02', 'status': 'ready', 'processed_path': 'dados_intermediarios/processed/brasil/pending.md'},
            {'document_id': 'DLGF-18', 'status': 'ready', 'processed_path': 'dados_intermediarios/processed/Unesco/dlgf.md'},
        ])

    monkeypatch.setattr(build_content_dataset, 'ROOT', tmp_path)
    monkeypatch.setattr(build_content_dataset, 'DOCUMENTS', documents_path)
    monkeypatch.setattr(build_content_dataset, 'PROCESSED', processed_path)
    output_path = tmp_path / 'round' / 'dataset_pages.jsonl'
    build_content_dataset.main(str(output_path))

    records = [json.loads(line) for line in output_path.read_text(encoding='utf-8').splitlines()]
    assert len(records) == 1
    assert records[0]['document_id'] == 'BR-01'
    assert records[0]['page_start'] == 8
    assert records[0]['validation_status'] == 'validated'

    with (output_path.parent / 'dataset_build_report.csv').open(encoding='utf-8-sig', newline='') as handle:
        report = {row['document_id']: row for row in csv.DictReader(handle)}
    assert report['BR-01']['record_status'] == 'included'
    assert report['BR-01']['pages_written'] == '1'
    assert report['BR-02']['record_status'] == 'excluded_not_previously_verified'
    assert report['DLGF-18']['record_status'] == 'excluded_non_national'


def test_index_is_built_from_page_dataset_and_preserves_provenance(tmp_path, monkeypatch):
    class FakeIndexer:
        def __init__(self):
            self.metadatas = []
            self.index = SimpleNamespace(ntotal=0)

        def add_batch(self, texts, metadatas, batch_size=8):
            self.index.ntotal += len(texts)
            self.metadatas.extend(metadatas)

        def validate_alignment(self):
            return self.index.ntotal == len(self.metadatas)

        def save(self, folder):
            output = Path(folder)
            output.mkdir(parents=True, exist_ok=True)
            (output / 'index.faiss').write_bytes(b'test-index')
            (output / 'metadatas.json').write_text(json.dumps(self.metadatas), encoding='utf-8')

    monkeypatch.setattr(build_index, 'Indexer', FakeIndexer)
    dataset_path = tmp_path / 'dataset_pages.jsonl'
    records = [
        {
            'content_id': 'BR-01_p0008_c001', 'document_id': 'BR-01',
            'country': 'Brasil', 'country_code': 'BR', 'source_scope': 'national',
            'validation_status': 'validated', 'processing_status': 'ready',
            'document_role': 'primary', 'source_path': 'brasil/curriculo.pdf',
            'document_title': 'Currículo BR', 'language': 'pt', 'year': '2024',
            'page_start': 8, 'page_end': 8,
            'source_text': 'Os estudantes desenvolvem programação e algoritmos.',
        },
        {
            'content_id': 'DLGF_p0001_c001', 'document_id': 'DLGF-18',
            'country': '', 'source_scope': 'international_reference',
            'validation_status': 'validated', 'page_start': 1,
            'source_text': 'Digital literacy framework reference.',
        },
    ]
    dataset_path.write_text(''.join(json.dumps(row) + '\n' for row in records), encoding='utf-8')

    output_dir = tmp_path / 'index'
    report = build_index.build_from_dataset(str(dataset_path), str(output_dir))
    metadata = json.loads((output_dir / 'metadatas.json').read_text(encoding='utf-8'))

    assert report['pages_indexed'] == 1
    assert report['records_excluded'] == 1
    assert metadata[0]['document_id'] == 'BR-01'
    assert metadata[0]['page_start'] == 8
    assert metadata[0]['validation_status'] == 'validated'
    assert (output_dir / 'build_report.json').exists()