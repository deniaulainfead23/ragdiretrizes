import json

from rag_project.build_dataset import build_bilingual_datasets


def test_build_bilingual_datasets_excludes_non_country_references(tmp_path):
    root = tmp_path / 'corpus'
    (root / 'unesco').mkdir(parents=True)
    (root / 'brasil').mkdir(parents=True)

    (root / 'unesco' / 'unesco_doc.txt').write_text('Education for sustainable development and global citizenship.', encoding='utf-8')
    (root / 'brasil' / 'curriculo_brasil.txt').write_text('A educação digital e o pensamento computacional no currículo brasileiro.', encoding='utf-8')

    registry = tmp_path / 'registry.yaml'
    registry.write_text('corpus_version: "3.0"\ntotal_countries: 1\ncountries: [{country_code: BR, country: brasil, continent: americas, include_in_analysis: true, documents: [{document_id: AM-BR-01, file: curriculo_brasil.txt, role: primary, validation_status: validated}]}, {country_code: UN, country: unesco, continent: international, include_in_analysis: true, documents: [{document_id: INT-UN-01, file: unesco_doc.txt, role: complementary, validation_status: validated}]}]\n', encoding='utf-8')

    out_dir = tmp_path / 'dataset_out'
    import rag_project.build_dataset as build_dataset_module
    original_loader = build_dataset_module.load_registry
    build_dataset_module.load_registry = lambda: original_loader(registry)
    try:
        build_bilingual_datasets(str(root), str(out_dir), use_openai_translation=False)
    finally:
        build_dataset_module.load_registry = original_loader

    original = out_dir / 'dataset_original.jsonl'
    assert original.exists()

    lines = [line for line in original.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(lines) == 1

    records = [json.loads(line) for line in lines]
    assert records[0]['country'] == 'brasil'
    assert records[0]['dataset_group'] == 'country'
    assert 'unesco_reference' not in records[0]
    assert 'pisa_reference' not in records[0]

    report_path = out_dir / 'dataset_build_report.csv'
    assert report_path.exists()
    with report_path.open(encoding='utf-8-sig', newline='') as handle:
        report = list(csv.DictReader(handle))
    assert len(report) == 2
    assert all(row['record_status'] == 'included' for row in report)
    assert all(row['translation_status'] == 'not_requested' for row in report)
    assert all('source_text' not in row for row in report)
