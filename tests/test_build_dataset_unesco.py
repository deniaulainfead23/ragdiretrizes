import json

from rag_project.build_dataset import build_bilingual_datasets


def test_build_bilingual_datasets_keeps_unesco_as_benchmark(tmp_path):
    root = tmp_path / 'corpus'
    (root / 'unesco').mkdir(parents=True)
    (root / 'brasil').mkdir(parents=True)

    (root / 'unesco' / 'unesco_doc.txt').write_text('Education for sustainable development and global citizenship.', encoding='utf-8')
    (root / 'brasil' / 'curriculo_brasil.txt').write_text('A educação digital e o pensamento computacional no currículo brasileiro.', encoding='utf-8')

    out_dir = tmp_path / 'dataset_out'
    build_bilingual_datasets(str(root), str(out_dir), use_openai_translation=False)

    original = out_dir / 'dataset_original.jsonl'
    assert original.exists()

    lines = [line for line in original.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(lines) >= 2

    records = [json.loads(line) for line in lines]
    grouped = {record['country']: record['dataset_group'] for record in records}

    assert grouped.get('unesco') == 'unesco'
    assert grouped.get('brasil') == 'country'
