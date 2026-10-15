import csv
import json
from pathlib import Path

import rag_project.validate_rag_run as batch


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0])
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_validate_run_reuses_existing_rows_and_writes_reports(monkeypatch, tmp_path):
    run_id = 'run-test'
    country_dir = tmp_path / run_id / 'countries' / 'brasil'
    country_dir.mkdir(parents=True)
    dataset_dir = tmp_path / 'pipeline_runs' / run_id / 'datasets'
    dataset_dir.mkdir(parents=True)
    (dataset_dir / 'dataset_original_pages.jsonl').write_text(
        json.dumps({
            'country': 'brasil',
            'source_scope': 'national',
            'document_id': 'DOC1',
            'source_path': 'corpus/brasil/documento.pdf',
            'page_start': 3,
            'source_text': 'Trecho literal.',
        }, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )
    write_csv(country_dir / 'respostas.csv', [{
        'response_id': 'R1',
        'question_id': 'Q02',
        'category_id': 'C02',
        'question_text': 'Pergunta de teste?',
        'response': 'Síntese parafraseada.',
        'validation_status': 'candidate',
        'run_date': '2026-10-03',
    }])
    write_csv(country_dir / 'evidencias.csv', [{
        'response_id': 'R1',
        'question_id': 'Q02',
        'evidence_id': 'E1',
        'document_id': 'DOC1',
        'source_text': 'Trecho literal.',
        'page_start': '3',
    }, {
        'response_id': 'OTHER',
        'question_id': 'Q02',
        'evidence_id': 'E2',
        'document_id': 'DOC2',
        'source_text': 'Não pertence a R1.',
        'page_start': '4',
    }])
    monkeypatch.setattr(batch, 'ANALYSIS_DIR', tmp_path)
    monkeypatch.setattr(batch, 'INTERMEDIATE_DATA_DIR', tmp_path)
    captured = []

    def fake_validate(question, country, answer, **kwargs):
        parsed = json.loads(answer)
        captured.append(parsed)
        return {
            'run_id': run_id,
            'country': country,
            'question_id': parsed['question_id'],
            'category_id': parsed['category_id'],
            'question': question,
            'answer': parsed['response'],
            'status': 'conteudo_duvidoso',
            'result_description': 'Teste.',
            'human_review_required': True,
            'citation_checks': [{'evidence_id': 'E1', 'citation_status': 'exact_text_on_cited_physical_page'}],
            'semantic_review': {'decision': 'doubtful', 'reason': 'Teste semântico.'},
            'reasons': ['Revisar.'],
        }

    monkeypatch.setattr(batch, 'validate_rag_answer', fake_validate)

    summary = batch.validate_run(run_id=run_id, output_dir=tmp_path / 'audit-output')

    assert summary['responses_processed'] == 1
    assert summary['citations_checked'] == 1
    assert captured[0]['evidences'][0]['evidence_id'] == 'E1'
    assert (tmp_path / 'audit-output' / 'validation_results.jsonl').is_file()
    assert (tmp_path / 'audit-output' / 'auditoria_respostas_rag.xlsx').is_file()
    assert summary['human_review_required_for_all'] is True
