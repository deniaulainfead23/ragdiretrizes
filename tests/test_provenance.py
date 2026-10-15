from pathlib import Path

from rag_project.build_bibliographic_matrix import build_bibliographic_matrix


def test_document_id_is_stable_for_same_file(tmp_path):
    corpus_root = tmp_path / 'corpus'
    country_dir = corpus_root / 'brasil'
    country_dir.mkdir(parents=True)
    source_path = country_dir / 'curriculo_brasil.txt'
    source_path.write_text('conteúdo do currículo brasileiro', encoding='utf-8')

    first = build_bibliographic_matrix(corpus_root, tmp_path / 'metadata_1')
    second = build_bibliographic_matrix(corpus_root, tmp_path / 'metadata_2')

    assert first[0]['document_id'] == second[0]['document_id']
    assert first[0]['sha256'] == second[0]['sha256']
