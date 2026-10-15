import json

from rag_project.sensitivity_analysis import build_sensitivity_report


def test_build_sensitivity_report_creates_files_and_summary(tmp_path):
    analysis_dir = tmp_path / 'analysis_output'
    analysis_dir.mkdir(parents=True, exist_ok=True)

    (analysis_dir / 'analysis_summary.json').write_text(
        json.dumps({
            'analysis_mode': 'exploratory_lexical',
            'documents': 4,
            'groups': ['Brasil', 'Canadá', 'Reino Unido'],
            'method_note': 'exploratory only'
        }),
        encoding='utf-8',
    )

    (analysis_dir / 'lexical_group_similarity.csv').write_text(
        'group_a,group_b,similarity\n'
        'Brasil,Canadá,0.71\n'
        'Brasil,Reino Unido,0.64\n'
        'Canadá,Reino Unido,0.82\n',
        encoding='utf-8',
    )

    report = build_sensitivity_report(analysis_dir, analysis_dir)

    assert report['runs'][0]['label'] == 'baseline'
    assert report['mean_similarity'] > 0
    assert (analysis_dir / 'sensitivity_results.csv').exists()
    assert (analysis_dir / 'sensitivity_summary.md').exists()
