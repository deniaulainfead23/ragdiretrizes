from pathlib import Path

from rag_project.build_bibliographic_matrix import build_bibliographic_matrix, build_corpus_manifest, build_country_selection


def test_build_bibliographic_matrix_and_hashes(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'brasil'
    country_dir.mkdir(parents=True)
    source_path = country_dir / 'curriculo_brasil.txt'
    source_path.write_text('A educação digital no Brasil e o pensamento computacional.', encoding='utf-8')

    metadata_dir = tmp_path / 'metadata'
    rows = build_bibliographic_matrix(corpus_root, metadata_dir)

    assert rows
    assert {'document_id', 'country', 'file_name', 'sha256', 'source_confidence', 'source_verified'}.issubset(rows[0].keys())
    assert rows[0]['country'] == 'Brasil'
    assert rows[0]['sha256']
    assert (metadata_dir / 'bibliographic_matrix.csv').exists()


def test_corpus_manifest_and_country_selection_are_created(tmp_path):
    corpus_root = tmp_path / 'corpus'
    (corpus_root / 'brasil').mkdir(parents=True)
    (corpus_root / 'australia').mkdir(parents=True)
    (corpus_root / 'brasil' / 'curriculo_brasil.txt').write_text('texto do brasil', encoding='utf-8')
    (corpus_root / 'australia' / 'curriculum_australia.txt').write_text('texto da australia', encoding='utf-8')

    metadata_dir = tmp_path / 'metadata'
    manifest_rows = build_corpus_manifest(corpus_root, metadata_dir)
    selection_rows = build_country_selection(corpus_root, metadata_dir)

    assert manifest_rows
    assert any(row['country'] == 'Brasil' for row in manifest_rows)
    assert any(row['country'] == 'Brasil' for row in selection_rows)
    assert all(row['sha256'] for row in manifest_rows)
    assert (metadata_dir / 'corpus_manifest.csv').exists()
    assert (metadata_dir / 'country_selection.csv').exists()
