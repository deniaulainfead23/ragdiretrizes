from rag_project.build_evidence_matrix import build_evidence_matrix, detect_framework_hits


def test_detect_framework_hits_returns_dlgf_areas():
    hits = detect_framework_hits('Students operate digital devices, hardware and software.')
    assert any(hit['framework_id'] == 'DLGF_2018' and hit['dimension_code'] == '0' for hit in hits)


def test_build_evidence_matrix_uses_only_validated_rag_evidence(tmp_path):
    evidence_path = tmp_path / 'evidencias.csv'
    with evidence_path.open('w', encoding='utf-8', newline='') as handle:
        import csv

        writer = csv.DictWriter(
            handle,
            fieldnames=['evidence_id', 'question_id', 'country', 'document_id', 'document_title', 'page_start', 'page_end', 'source_text', 'validation_status'],
        )
        writer.writeheader()
        writer.writerow({
            'evidence_id': 'ev-1', 'question_id': 'Q04', 'country': 'Brasil',
            'document_id': 'BR_001', 'document_title': 'Currículo de Computação',
            'page_start': '7', 'page_end': '7',
            'source_text': 'Students operate digital devices, hardware and software.',
            'validation_status': 'validated',
        })
        writer.writerow({
            'evidence_id': 'ev-2', 'question_id': 'Q04', 'country': 'Brasil',
            'document_id': 'BR_002', 'document_title': 'Documento pendente',
            'page_start': '2', 'page_end': '2', 'source_text': 'digital devices',
            'validation_status': 'candidate',
        })

    output_dir = tmp_path / 'analysis' / 'evidence'
    rows = build_evidence_matrix(evidence_path, output_dir)

    assert len(rows) == 1
    assert (output_dir / 'evidence_matrix.csv').exists()
    assert rows[0]['document_id'] == 'BR_001'
    assert rows[0]['framework_id'] == 'DLGF_2018'
    assert rows[0]['area_code'] == '0'
    assert rows[0]['validation_status'] == 'validated'
