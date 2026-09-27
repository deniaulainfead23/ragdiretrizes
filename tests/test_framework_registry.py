import json
from pathlib import Path

from rag_project.analyze_tfidf import analyze
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
