from rag_project.build_evidence_matrix import classify_evidence_record


def test_evidence_record_classification_uses_local_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    record = classify_evidence_record(
        snippet='Os estudantes desenvolvem pensamento crítico e empatia para participar de questões globais.',
        framework_id='UNESCO_GCED_2015',
        dimension_code='COG',
        dimension_name='Cognitive',
    )

    assert record['evidence_classification'] == 'explicit'
    assert record['evidence_status'] in {'candidate', 'validated'}
    assert 'manual' in record['validation_notes'].lower() or 'fallback' in record['validation_notes'].lower()
