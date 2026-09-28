import json

from rag_project.run_curated_pipeline import audit_corpus, build_english_page_dataset, build_page_dataset


def test_audit_blocks_build_when_corpus_has_curation_divergences(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'canada'
    country_dir.mkdir(parents=True)
    (country_dir / 'approved.pdf').write_bytes(b'%PDF approved')
    (country_dir / 'pending.pdf').write_bytes(b'%PDF pending')
    (country_dir / 'unregistered.pdf').write_bytes(b'%PDF unregistered')

    registry = {
        'countries': [
            {
                'country': 'canada',
                'include_in_analysis': True,
                'documents': [
                    {'document_id': 'CA-01', 'file': 'approved.pdf', 'role': 'primary', 'validation_status': 'validated'},
                    {'document_id': 'CA-02', 'file': 'missing.pdf', 'role': 'primary', 'validation_status': 'validated'},
                    {'document_id': 'CA-03', 'file': 'pending.pdf', 'role': 'primary', 'validation_status': 'pending_review'},
                ],
            }
        ]
    }

    audit = audit_corpus(corpus_root, registry)

    assert audit['verified_present_documents'] == 1
    assert audit['missing_verified_files'] == ['canada/missing.pdf']
    assert audit['unregistered_excluded_files'] == ['canada/unregistered.pdf']
    assert audit['pending_verification_excluded_files'] == ['canada/pending.pdf']
    assert audit['is_buildable'] is False


def test_audit_allows_build_for_fully_curated_corpus(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'canada'
    country_dir.mkdir(parents=True)
    (country_dir / 'approved.pdf').write_bytes(b'%PDF approved')
    registry = {
        'countries': [
            {
                'country': 'canada',
                'include_in_analysis': True,
                'documents': [
                    {'document_id': 'CA-01', 'file': 'approved.pdf', 'role': 'primary', 'validation_status': 'validated'},
                ],
            }
        ]
    }

    audit = audit_corpus(corpus_root, registry)

    assert audit['is_buildable'] is True


def test_exploratory_dataset_includes_pending_without_relabeling(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'brasil'
    country_dir.mkdir(parents=True)
    (country_dir / 'approved.txt').write_text('Texto validado.', encoding='utf-8')
    (country_dir / 'pending.txt').write_text('Texto ainda pendente.', encoding='utf-8')
    registry = {
        'countries': [{
            'country': 'brasil',
            'country_code': 'BR',
            'include_in_analysis': True,
            'documents': [
                {'document_id': 'BR-01', 'file': 'approved.txt', 'role': 'primary', 'validation_status': 'validated'},
                {'document_id': 'BR-02', 'file': 'pending.txt', 'role': 'complementary', 'validation_status': 'pending_review'},
            ],
        }]
    }
    output = tmp_path / 'run' / 'dataset_pages.jsonl'

    report = build_page_dataset(corpus_root, output, registry, include_pending_review=True)

    records = [json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
    assert report['documents_included'] == 2
    assert report['validation_status_counts'] == {'validated': 1, 'pending_review': 1}
    assert {record['document_id']: record['validation_status'] for record in records} == {
        'BR-01': 'validated',
        'BR-02': 'pending_review',
    }


def test_pending_and_unregistered_sources_do_not_block_validated_subset(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'canada'
    country_dir.mkdir(parents=True)
    for name in ('approved.pdf', 'pending.pdf', 'unregistered.pdf'):
        (country_dir / name).write_bytes(b'%PDF')
    registry = {
        'countries': [{
            'country': 'canada',
            'include_in_analysis': True,
            'documents': [
                {'document_id': 'CA-01', 'file': 'approved.pdf', 'role': 'primary', 'validation_status': 'validated'},
                {'document_id': 'CA-02', 'file': 'pending.pdf', 'role': 'complementary', 'validation_status': 'pending_review'},
            ],
        }]
    }

    audit = audit_corpus(corpus_root, registry)

    assert audit['verified_present_documents'] == 1
    assert audit['pending_verification_excluded_files'] == ['canada/pending.pdf']
    assert audit['unregistered_excluded_files'] == ['canada/unregistered.pdf']
    assert audit['is_buildable'] is True


def test_run_local_dataset_extracts_only_validated_registry_documents(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'canada'
    country_dir.mkdir(parents=True)
    (country_dir / 'approved.txt').write_text('Currículo oficial de computação.', encoding='utf-8')
    (country_dir / 'pending.txt').write_text('Documento pendente.', encoding='utf-8')
    registry = {
        'countries': [{
            'country': 'canada',
            'country_code': 'CA',
            'include_in_analysis': True,
            'documents': [
                {'document_id': 'CA-01', 'file': 'approved.txt', 'role': 'primary', 'validation_status': 'validated'},
                {'document_id': 'CA-02', 'file': 'pending.txt', 'role': 'primary', 'validation_status': 'pending_review'},
            ],
        }]
    }
    output = tmp_path / 'run' / 'dataset_pages.jsonl'

    report = build_page_dataset(corpus_root, output, registry)

    records = [json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
    assert report['documents_included'] == 1
    assert report['pages_written'] == 1
    assert [record['document_id'] for record in records] == ['CA-01']
    assert records[0]['source_text'] == 'Currículo oficial de computação.'


def test_english_dataset_preserves_original_source_crosswalk(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / 'dataset_original_pages.jsonl'
    source.write_text(json.dumps({
        'content_id': 'JP-01_p0001',
        'document_id': 'JP-01',
        'country': 'japao',
        'source_scope': 'national',
        'validation_status': 'validated',
        'page_start': 1,
        'source_text': '情報技術を教育に活用する。',
    }, ensure_ascii=False) + '\n', encoding='utf-8')
    output = tmp_path / 'dataset_english_pages.jsonl'

    report = build_english_page_dataset(
        source,
        output,
        api_key='',
        cache_path=tmp_path / 'translation_cache.json',
        translator=lambda value: 'Use information technology in education.',
    )

    row = json.loads(output.read_text(encoding='utf-8').splitlines()[0])
    assert report['source_pages'] == 1
    assert row['source_text'] == 'Use information technology in education.'
    assert row['original_text'] == '情報技術を教育に活用する。'
    assert row['translation_status'] == 'translated'
