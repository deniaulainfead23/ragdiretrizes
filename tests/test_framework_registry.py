import json
from pathlib import Path

from rag_project.analyze_tfidf import analyze, analyze_dlgf_only, analyze_within_country
from rag_project.build_evidence_matrix import build_evidence_matrix
from rag_project.framework_registry import (
    export_framework_csvs,
    get_framework_by_id,
    list_frameworks,
    load_excluded_entities,
    load_preprocessing_rules,
    load_stopwords,
)


def test_only_dlgf_and_computing_frameworks_are_active():
    assert set(list_frameworks()) == {'DLGF_2018', 'COMPUTING_AND_DIGITAL_EDUCATION'}


def test_dlgf_framework_has_expected_areas():
    framework = get_framework_by_id('DLGF_2018')
    assert framework is not None
    assert framework['version'] == '3.0'
    codes = {d['code'] for d in framework['dimensions']}
    assert {'0', '1', '2', '3', '4', '5', '6'} <= codes


def test_computing_framework_has_expected_domains():
    framework = get_framework_by_id('COMPUTING_AND_DIGITAL_EDUCATION')
    assert framework is not None
    assert framework['version'] == '2.0'
    assert any(d['code'] == 'COMP' for d in framework['domains'])
    assert any(d['code'] == 'DIG' for d in framework['domains'])


def test_stopwords_and_preprocessing_rules_are_defined():
    documental = load_stopwords('documental')
    language = load_stopwords('language')
    assert 'sobre' in documental
    assert 'the' in language

    rules = load_preprocessing_rules()
    assert rules['lowercase'] is True
    assert rules['remove_punctuation'] is True


def test_framework_exports_and_excluded_entities_are_ready():
    outputs = export_framework_csvs()
    framework_dir = Path(__file__).resolve().parent.parent / 'rag_project' / 'framework'

    assert framework_dir.joinpath('computing_framework.csv').exists()
    assert set(outputs) == {'DLGF_2018', 'COMPUTING_AND_DIGITAL_EDUCATION'}
    assert framework_dir.joinpath('unesco_dlgf_2018.csv').exists()
    assert 'COMPUTING_AND_DIGITAL_EDUCATION' in outputs

    excluded = load_excluded_entities()
    assert 'documento' in excluded
    assert 'currículo' in excluded or 'curriculo' in excluded


def test_tfidf_analysis_is_explicitly_exploratory_and_lexical(tmp_path):
    input_path = tmp_path / 'dataset.jsonl'
    records = [
        {
            'country': 'Brasil',
            'document': 'doc_brasil_1',
            'dataset_group': 'country',
            'english_text': 'digital literacy programming and citizenship in education',
        },
        {
            'country': 'Canada',
            'document': 'doc_canada_1',
            'dataset_group': 'country',
            'english_text': '',
            'source_text': 'digital citizenship technology use and critical thinking in schools',
        },
        {
            'country': 'Irlanda',
            'document': 'doc_irlanda_1',
            'dataset_group': 'country',
            'english_text': 'digital information security and programming in the curriculum',
        },
    ]
    with input_path.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record) + '\n')

    output_dir = tmp_path / 'analysis_output'
    analyze(str(input_path), str(output_dir), text_field='english_text', top_n=5)

    summary = json.loads((output_dir / 'analysis_summary.json').read_text(encoding='utf-8'))
    assert summary['analysis_mode'] == 'exploratory_lexical'
    assert (output_dir / 'lexical_group_similarity.csv').exists()
    assert (output_dir / 'lexical_group_similarity_heatmap.png').exists()
    assert (output_dir / 'group_tfidf.csv').exists()
    assert (output_dir / 'group_similarity_heatmap.png').exists()

    group_rows = list(__import__('csv').DictReader((output_dir / 'group_tfidf.csv').open('r', encoding='utf-8', newline='')))
    assert all(row['group'] not in {'UNESCO', 'PISA', 'OECD/PISA'} for row in group_rows)


def test_within_country_tfidf_avoids_cross_country_scores_and_flags_cjk(tmp_path):
    input_path = tmp_path / 'dataset.jsonl'
    records = [
        {'country': 'brasil', 'document_id': 'br1', 'source_scope': 'national', 'source_text': 'programação dados algoritmos resolução problemas'},
        {'country': 'brasil', 'document_id': 'br2', 'source_scope': 'national', 'source_text': 'programação digital dados criação conteúdo'},
        {'country': 'taiwan', 'document_id': 'tw1', 'source_scope': 'national', 'source_text': '數位合作共創 演算法 資料處理'},
        {'country': 'taiwan', 'document_id': 'tw2', 'source_scope': 'national', 'source_text': '資訊科技 程式設計 資料處理'},
        {'country': 'coreia-do-sul', 'document_id': 'kr1', 'source_scope': 'national', 'source_text': '컴퓨터 교육과 정보 기술'},
        {'country': 'coreia-do-sul', 'document_id': 'kr2', 'source_scope': 'national', 'source_text': '디지털 정보 보호와 프로그래밍'},
        {'country': 'uruguai', 'document_id': 'uy1', 'source_scope': 'national', 'source_text': 'tecnologías digitales educación básica'},
        {'country': 'UNESCO', 'document_id': 'u1', 'source_scope': 'international_reference', 'source_text': 'digital literacy devices data'},
    ]
    with input_path.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')

    output_dir = tmp_path / 'within_country_output'
    summary = analyze_within_country(str(input_path), str(output_dir), text_field='source_text', top_n=5)

    assert summary['mode'] == 'within_country_only'
    assert summary['cross_country_similarity_computed'] is False
    assert summary['dlgf_similarity_computed'] is False
    assert summary['analysis_status_counts']['translation_required_cjk'] == 2
    assert not (output_dir / 'lexical_group_similarity.csv').exists()
    assert not (output_dir / 'country_dlgf_area_similarity.csv').exists()
    profiles = list(__import__('csv').DictReader((output_dir / 'country_profiles.csv').open(encoding='utf-8', newline='')))
    taiwan = next(row for row in profiles if row['country'] == 'taiwan')
    assert taiwan['analysis_status'] == 'translation_required_cjk'
    korea = next(row for row in profiles if row['country'] == 'coreia-do-sul')
    assert korea['analysis_status'] == 'translation_required_cjk'
    uruguay = next(row for row in profiles if row['country'] == 'uruguai')
    assert uruguay['analysis_status'] == 'single_document_no_idf_contrast'
    terms = list(__import__('csv').DictReader((output_dir / 'country_local_top_terms.csv').open(encoding='utf-8', newline='')))
    assert any(row['country'] == 'uruguai' for row in terms)


def test_within_country_tfidf_removes_english_function_words(tmp_path):
    input_path = tmp_path / 'translated_dataset.jsonl'
    records = [
        {'country': 'japao', 'document_id': 'jp1', 'source_scope': 'national', 'source_text': 'That is the digital programming curriculum and it will teach algorithms.'},
        {'country': 'japao', 'document_id': 'jp2', 'source_scope': 'national', 'source_text': 'This curriculum should teach students programming, data, and algorithms.'},
    ]
    with input_path.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')

    output_dir = tmp_path / 'translated_output'
    analyze_within_country(str(input_path), str(output_dir), text_field='source_text', top_n=20)

    rows = list(__import__('csv').DictReader((output_dir / 'country_local_top_terms.csv').open(encoding='utf-8', newline='')))
    terms = {row['term'] for row in rows}
    assert {'that', 'the', 'will', 'this', 'should', 'and'} .isdisjoint(terms)
    assert 'algorithms' in terms


def test_dlgf_only_tfidf_outputs_country_to_framework_without_country_ranking(tmp_path):
    input_path = tmp_path / 'translated_dataset.jsonl'
    records = [
        {'country': 'japao', 'document_id': 'jp1', 'source_scope': 'national', 'english_text': 'Students use algorithms and programming to solve problems.'},
        {'country': 'eua', 'document_id': 'us1', 'source_scope': 'national', 'english_text': 'Students use devices, software, data, privacy, and programming.'},
        {'country': 'unesco', 'document_id': 'other', 'source_scope': 'international_reference', 'english_text': 'Unrelated reference vocabulary.'},
    ]
    with input_path.open('w', encoding='utf-8') as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')

    output_dir = tmp_path / 'dlgf_only'
    summary = analyze_dlgf_only(
        str(input_path),
        str(output_dir),
        framework_path=Path(__file__).resolve().parent.parent / 'rag_project' / 'framework' / 'unesco_dlgf_2018.csv',
        asset_dir=tmp_path / 'assets',
    )

    rows = list(__import__('csv').DictReader((output_dir / 'country_dlgf_area_similarity.csv').open(encoding='utf-8', newline='')))
    assert summary['analysis_mode'] == 'country_to_dlgf_only'
    assert summary['framework_area_count'] == 7
    assert summary['countries'] == ['eua', 'japao']
    assert summary['country_country_similarity_computed'] is False
    assert summary['other_frameworks_included'] == []
    assert len(rows) == 14
    assert {row['framework_id'] for row in rows} == {'DLGF_2018'}
    assert not (output_dir / 'country_similarity.csv').exists()
    assert (tmp_path / 'assets' / 'country_dlgf_area_similarity_heatmap.png').is_file()


def test_dlgf_matrix_distinguishes_translation_and_review_states(tmp_path):
    source = tmp_path / 'evidence.csv'
    source.write_text(
        'country,question_id,evidence_id,document_id,original_text,evidence_validation_status\n'
        'japao,Q01,J1,DOC1,情報技術を適切かつ効果的に活用する力,validada\n'
        'singapura,Q01,S1,DOC2,"programming and algorithms",validada\n',
        encoding='utf-8',
    )
    build_evidence_matrix(source, tmp_path / 'out')
    matrix = list(__import__('csv').DictReader((tmp_path / 'out' / 'dlgf_country_area_matrix.csv').open(encoding='utf-8-sig')))
    japan = next(row for row in matrix if row['country'] == 'japao')
    singapore = next(row for row in matrix if row['country'] == 'singapura')
    assert len([key for key in japan if key.startswith('CA')]) == 7
    assert japan['assessment_status'] == 'translation_required'
    assert japan['CA3_Digital content creation'] == 'translation_required'
    assert singapore['assessment_status'] == 'reviewed_sample'
    assert singapore['CA3_Digital content creation'] != 'no_match_in_reviewed_sample'
