from pathlib import Path

from rag_project.country_framework_comparison import aggregate_country_framework_summary


def test_aggregate_country_framework_summary_returns_country_rows(tmp_path):
    evidence_csv = tmp_path / 'evidence_matrix.csv'
    evidence_csv.write_text(
        'evidence_id,country,document_id,framework_id,area_code,area_name,correspondence,validation_status\n'
        'ev-1,Brasil,BR_001,DLGF_2018,0,Devices and software operations,strong,validated\n'
        'ev-2,Estados Unidos,US_001,DLGF_2018,5,Problem-solving,candidate,validated\n'
        'ev-3,Estados Unidos,US_001,DLGF_2018,4,Safety,candidate,candidate\n',
        encoding='utf-8',
    )

    rows = aggregate_country_framework_summary(evidence_csv)

    assert rows
    assert any(r['country'] == 'Brasil' and r['framework_id'] == 'DLGF_2018' and r['area_code'] == '0' for r in rows)
    assert any(r['country'] == 'Estados Unidos' and r['framework_id'] == 'DLGF_2018' and r['area_code'] == '5' for r in rows)
    assert not any(r['area_code'] == '4' for r in rows)
    assert rows[0]['evidence_count'] >= 1
