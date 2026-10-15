import json

from rag_project.run_curated_pipeline import audit_corpus, build_english_page_dataset, build_page_dataset
from rag_project.run_tfidf_all_countries import (
    export_tfidf_chart_assets,
    generate_tfidf_charts,
    verify_translation_coverage,
)


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


def test_tfidf_translation_coverage_requires_every_source_page(tmp_path):
    source = tmp_path / 'source.jsonl'
    source.write_text(
        '\n'.join([
            json.dumps({'content_id': 'JP_p0001', 'country': 'japao', 'source_text': '日本語。'}, ensure_ascii=False),
            json.dumps({'content_id': 'BR_p0001', 'country': 'brasil', 'source_text': 'Texto.'}, ensure_ascii=False),
        ]) + '\n',
        encoding='utf-8',
    )
    translated = tmp_path / 'translated.jsonl'
    translated.write_text(
        '\n'.join([
            json.dumps({'page_content_id': 'JP_p0001', 'country': 'japao', 'language': 'en', 'translation_status': 'translated', 'english_text': 'Japanese text.'}),
            json.dumps({'page_content_id': 'BR_p0001', 'country': 'brasil', 'language': 'en', 'translation_status': 'translated', 'english_text': 'Text.'}),
        ]) + '\n',
        encoding='utf-8',
    )

    coverage = verify_translation_coverage(source, translated)

    assert coverage['source_pages'] == 2
    assert coverage['translated_pages'] == 2
    assert coverage['countries'] == ['brasil', 'japao']


def test_tfidf_translation_coverage_rejects_missing_pages(tmp_path):
    source = tmp_path / 'source.jsonl'
    source.write_text(
        json.dumps({'content_id': 'JP_p0001', 'country': 'japao', 'source_text': '日本語。'}) + '\n',
        encoding='utf-8',
    )
    translated = tmp_path / 'translated.jsonl'
    translated.write_text('', encoding='utf-8')

    try:
        verify_translation_coverage(source, translated)
    except ValueError as exc:
        assert 'Tradução incompleta' in str(exc)
    else:
        raise AssertionError('A cobertura incompleta deveria ser rejeitada.')


def test_tfidf_chart_generation_marks_countries_without_contrast(tmp_path):
    analysis_dir = tmp_path / 'analysis'
    analysis_dir.mkdir()
    (analysis_dir / 'country_profiles.csv').write_text(
        'country,documents,analysis_status\njapao,3,within_country_only\neua,1,single_document_no_idf_contrast\n',
        encoding='utf-8',
    )
    (analysis_dir / 'country_local_top_terms.csv').write_text(
        'country,rank_within_country,term,mean_tfidf_within_country\n'
        'japao,1,students,0.04\njapao,2,learning,0.03\njapao,3,technology,0.02\n'
        'eua,1,students,0.05\neua,2,computing,0.04\neua,3,technology,0.03\n',
        encoding='utf-8',
    )

    report = generate_tfidf_charts(analysis_dir)

    assert report['country_charts'] == 2
    assert report['countries_without_idf_contrast'] == ['eua']
    assert report['countries_without_terms'] == []
    assert (analysis_dir / 'top3_terms_by_country.png').is_file()
    assert (analysis_dir / 'countries' / 'japao_tfidf_top3.png').is_file()
    assert (analysis_dir / 'countries' / 'eua_tfidf_top3.png').is_file()

    assets = export_tfidf_chart_assets(report, tmp_path / 'tfidf_run', tmp_path / 'assets')
    assert (tmp_path / 'assets' / 'tfidf_run' / 'top3_terms_by_country.png').is_file()
    assert (tmp_path / 'assets' / 'tfidf_run' / 'countries' / 'japao_tfidf_top3.png').is_file()
