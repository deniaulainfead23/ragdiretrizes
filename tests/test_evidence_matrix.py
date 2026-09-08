import csv

from rag_project.build_evidence_matrix import build_evidence_matrix, detect_framework_hits


def test_detect_framework_hits_recognizes_unesco_dimensions():
    text = (
        'Students should develop critical thinking and empathy, with participation in global citizenship '
        'activities and collaborative problem solving.'
    )

    hits = detect_framework_hits(text)

    assert any(hit['framework_id'] == 'UNESCO_GCED_2015' and hit['dimension_code'] == 'COG' for hit in hits)
    assert any(hit['framework_id'] == 'UNESCO_GCED_2015' and hit['dimension_code'] == 'SOE' for hit in hits)
    assert any(hit['framework_id'] == 'UNESCO_GCED_2015' and hit['dimension_code'] == 'BEH' for hit in hits)


def test_build_evidence_matrix_creates_auditable_csv(tmp_path):
    corpus_dir = tmp_path / 'corpus' / 'brasil'
    corpus_dir.mkdir(parents=True)
    (corpus_dir / 'brasil_curriculum.txt').write_text(
        'Os estudantes devem desenvolver pensamento crítico, empatia e participação ativa em cidadania global.',
        encoding='utf-8',
    )

    metadata_dir = tmp_path / 'metadata'
    metadata_dir.mkdir(parents=True)
    meta_path = metadata_dir / 'bibliographic_matrix.csv'
    with meta_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['document_id', 'country', 'title_original', 'relative_path', 'file_name'])
        writer.writeheader()
        writer.writerow({
            'document_id': 'BR_001',
            'country': 'Brasil',
            'title_original': 'brasil_curriculum',
            'relative_path': 'brasil/brasil_curriculum.txt',
            'file_name': 'brasil_curriculum.txt',
        })

    output_dir = tmp_path / 'analysis' / 'evidence'
    rows = build_evidence_matrix(corpus_root=tmp_path / 'corpus', metadata_csv=meta_path, output_dir=output_dir)

    assert rows
    assert (output_dir / 'evidence_matrix.csv').exists()
    assert rows[0]['document_id'] == 'BR_001'
    assert rows[0]['framework_id'] == 'UNESCO_GCED_2015'
    assert rows[0]['evidence_classification'] == 'explicit'
