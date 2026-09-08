from pathlib import Path

from rag_project.country_framework_comparison import aggregate_country_framework_summary


def test_aggregate_country_framework_summary_returns_country_rows(tmp_path):
    evidence_csv = tmp_path / 'evidence_matrix.csv'
    evidence_csv.write_text(
        'document_id,country,title_original,framework_id,dimension_code,dimension_name,matched_keyword,matched_text,evidence_classification,evidence_status,validation_notes,source_file\n'
        'BR_001,Brasil,brasil_curriculum,UNESCO_GCED_2015,COG,Cognitive,pensamento crítico,"Os estudantes desenvolvem pensamento crítico e empatia.",explicit,validated,"OpenAI validation",brasil/brasil_curriculum.txt\n'
        'BR_001,Brasil,brasil_curriculum,UNESCO_GCED_2015,SOE,Socioemotional,empatia,"Os estudantes desenvolvem pensamento crítico e empatia.",explicit,validated,"OpenAI validation",brasil/brasil_curriculum.txt\n'
        'US_001,Estados Unidos,us_framework,UNESCO_GCED_2015,COG,Cognitive,critical thinking,"Students build critical thinking.",explicit,validated,"OpenAI validation",us/us_framework.txt\n',
        encoding='utf-8',
    )

    rows = aggregate_country_framework_summary(evidence_csv)

    assert rows
    assert any(r['country'] == 'Brasil' and r['framework_id'] == 'UNESCO_GCED_2015' and r['dimension_code'] == 'COG' for r in rows)
    assert any(r['country'] == 'Estados Unidos' and r['framework_id'] == 'UNESCO_GCED_2015' and r['dimension_code'] == 'COG' for r in rows)
    assert rows[0]['evidence_count'] >= 1
