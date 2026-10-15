from rag_project.build_evidence_matrix import classify_evidence_record


def test_evidence_record_classification_is_preliminary_and_dlgf_only():
    record = classify_evidence_record(
        snippet='Students operate digital devices and software.',
        framework_id='DLGF_2018',
        dimension_code='0',
        dimension_name='Devices and software operations',
    )

    assert record['evidence_classification'] == 'explicit'
    assert record['evidence_status'] == 'candidate'
    assert 'humana' in record['validation_notes'].lower()
