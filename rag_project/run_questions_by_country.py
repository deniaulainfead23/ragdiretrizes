from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from rag_project.question_catalog import get_questions
from rag_project.corpus_registry import get_country, load_registry, registered_documents
from rag_project.rag.query import rag_query
from rag_project.vector_backend import resolve_backend
from rag_project.openai_vector_store import cloud_rag_query

PROMPT_VERSION = "rag-country-v3.1"


def build_country_question_plan(country: str, question_id: str | None = None) -> list[dict]:
    questions = get_questions()
    selected = []
    for q in questions:
        if q.get('question_type') != 'evidence_retrieval':
            continue
        if question_id and q.get('question_id') != question_id:
            continue
        if q.get('target_country') in {None, country, country.lower()}:
            selected.append({
                'question_id': q['question_id'],
                'title': q['title'],
                'question_text': q['question_text'],
                'target_country': q.get('target_country') or country,
                'question_type': q['question_type'],
                'analysis_stage': q['analysis_stage'],
                'framework': q['framework'],
                'category_id': q['category_id'],
                'version': q['version'],
            })
    if question_id and not selected:
        raise ValueError(f'Pergunta não encontrada ou não aplicável ao país: {question_id}')
    return selected


def _structured_question_text(item: dict, country: str) -> str:
    return (
        f"{item['question_text']}\n\n"
        "Regras de saída: responda SOMENTE em JSON válido, sem bloco Markdown. "
        "Use as chaves question_id, country, response, evidences e validation_status. "
        "evidences deve ser uma lista de objetos contendo evidence_id, document_id, "
        "document_title, page_start, page_end, chunk_id, source_text, semantic_score, "
        "evidence_classification e validation_status. Preserve o trecho no idioma original. "
        "Não invente página, documento, chunk_id ou evidência. Se a recuperação for insuficiente, "
        "registre validation_status como inconclusive. "
        f"question_id={item['question_id']}; country={country}; "
        f"analysis_framework={item['framework']}; category_id={item['category_id']}."
    )


def _parse_response(response: str) -> dict:
    try:
        value = json.loads(response)
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _write_csv(path: Path, rows: list[dict], fallback_fields: list[str]) -> None:
    fields = list(rows[0].keys()) if rows else fallback_fields
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_question_plan(
    country: str,
    output_dir: str | Path,
    index_folder: str = 'indexed',
    openai_api_key: str | None = None,
    vector_store_id: str | None = None,
    backend: str | None = None,
    question_id: str | None = None,
) -> list[dict]:
    plan = build_country_question_plan(country, question_id=question_id)
    registry = load_registry()
    country_entry = get_country(registry, country)
    if not country_entry or not country_entry.get('include_in_analysis'):
        raise ValueError(f'País não está ativo no registro: {country}')

    documents = list(registered_documents(registry, country))
    document_ids = [document['document_id'] for _, document in documents]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    resolved_backend = resolve_backend(backend, openai_api_key)
    if resolved_backend == 'openai' and not vector_store_id:
        raise ValueError('vector_store_id é obrigatório quando o backend OpenAI é selecionado')

    run_timestamp = datetime.now(timezone.utc)
    run_stamp = run_timestamp.strftime('%Y%m%dT%H%M%SZ')
    run_id = f"RUN_{country.upper().replace('-', '_')}_{run_stamp}"

    run_entries: list[dict] = []
    response_rows: list[dict] = []
    evidence_rows: list[dict] = []

    for item in plan:
        question_run_id = f"{run_id}_{item['question_id']}"
        response_id = f"RESP_{country.upper().replace('-', '_')}_{item['question_id']}_{run_stamp}"

        if resolved_backend == 'openai':
            # IMPORTANTE: o filtro do Vector Store é exclusivamente por país.
            # item['framework'] é framework analítico da pergunta, não framework_source do documento.
            response = cloud_rag_query(
                vector_store_id,
                _structured_question_text(item, country),
                openai_api_key,
                question_id=item['question_id'],
                country=country,
                framework='',
                category_id=item['category_id'],
            )
        else:
            response = rag_query(
                index_folder,
                item['question_text'],
                item['question_id'],
                country,
                item['framework'],
                item['category_id'],
                document_ids,
                top_k=10,
                openai_api_key=openai_api_key,
                question_version=str(item['version']),
            )

        parsed = _parse_response(response)
        evidences = parsed.get('evidences', [])
        if not isinstance(evidences, list):
            evidences = []

        evidence_ids: list[str] = []
        for position, evidence in enumerate(evidences, start=1):
            if not isinstance(evidence, dict):
                continue
            evidence_id = str(
                evidence.get('evidence_id')
                or f"EVID_{country.upper().replace('-', '_')}_{item['question_id']}_{position:03d}_{run_stamp}"
            )
            evidence_ids.append(evidence_id)
            evidence_rows.append({
                'evidence_id': evidence_id,
                'run_id': run_id,
                'question_run_id': question_run_id,
                'response_id': response_id,
                'question_id': item['question_id'],
                'category_id': item['category_id'],
                'framework': item['framework'],
                'country': country,
                'document_id': evidence.get('document_id', ''),
                'document_title': evidence.get('document_title') or evidence.get('documento', ''),
                'page_start': evidence.get('page_start') or evidence.get('page', ''),
                'page_end': evidence.get('page_end') or evidence.get('page', ''),
                'chunk_id': evidence.get('chunk_id', ''),
                'source_text': evidence.get('source_text') or evidence.get('trecho_original', ''),
                'translated_text': evidence.get('translated_text', ''),
                'semantic_score': evidence.get('semantic_score', ''),
                'evidence_classification': evidence.get('evidence_classification') or evidence.get('classification', ''),
                'validation_status': evidence.get('validation_status', 'candidate'),
                'review_notes': '',
            })

        if not evidence_ids:
            legacy_ids = parsed.get('evidence_ids', [])
            if isinstance(legacy_ids, list):
                evidence_ids = [str(value) for value in legacy_ids]

        response_text = parsed.get('response', '') if parsed else ''
        if not response_text:
            response_text = response

        validation_status = parsed.get('validation_status', 'candidate') if parsed else 'unparsed'
        response_rows.append({
            'response_id': response_id,
            'run_id': run_id,
            'question_run_id': question_run_id,
            'question_id': item['question_id'],
            'category_id': item['category_id'],
            'framework': item['framework'],
            'country': country,
            'question_text': item['question_text'],
            'response': response_text,
            'evidence_ids': '; '.join(evidence_ids),
            'backend': resolved_backend,
            'question_version': item['version'],
            'prompt_version': PROMPT_VERSION,
            'run_date': run_timestamp.isoformat(),
            'validation_status': validation_status,
            'review_notes': '',
        })

        run_entries.append({
            'run_id': run_id,
            'question_run_id': question_run_id,
            'response_id': response_id,
            'question_id': item['question_id'],
            'country': country,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'framework': item['framework'],
            'category_id': item['category_id'],
            'question_version': item['version'],
            'prompt_version': PROMPT_VERSION,
            'backend': resolved_backend,
            'status': 'executed',
            'number_of_evidences': len(evidence_ids),
        })

    _write_csv(
        out_dir / 'question_run_log.csv',
        run_entries,
        ['run_id', 'question_id', 'country'],
    )
    _write_csv(
        out_dir / 'evidencias.csv',
        evidence_rows,
        [
            'evidence_id', 'run_id', 'question_run_id', 'response_id', 'question_id',
            'category_id', 'framework', 'country', 'document_id', 'document_title',
            'page_start', 'page_end', 'chunk_id', 'source_text', 'translated_text',
            'semantic_score', 'evidence_classification', 'validation_status', 'review_notes',
        ],
    )
    _write_csv(
        out_dir / 'respostas.csv',
        response_rows,
        [
            'response_id', 'run_id', 'question_run_id', 'question_id', 'category_id',
            'framework', 'country', 'question_text', 'response', 'evidence_ids', 'backend',
            'question_version', 'prompt_version', 'run_date', 'validation_status', 'review_notes',
        ],
    )

    return plan


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / '.env')
    parser = argparse.ArgumentParser(
        description='Executa perguntas de recuperação por país e gera datasets identificados de evidências e respostas.'
    )
    parser.add_argument('--country', required=True, help='País para executar as perguntas')
    parser.add_argument('--out', default=None, help='Diretório de saída; padrão analysis/countries/<country>')
    parser.add_argument('--index', default='indexed', help='Pasta do índice local')
    parser.add_argument('--openai_key', default=None, help='Chave OpenAI opcional')
    parser.add_argument('--vector_store_id', default=None, help='ID do OpenAI Vector Store')
    parser.add_argument('--backend', default=None, choices=['openai', 'local'], help='Backend de recuperação')
    parser.add_argument('--question_id', default=None, help='Executa apenas uma pergunta, por exemplo Q01')
    args = parser.parse_args()

    output_dir = args.out or str(Path('analysis') / 'countries' / args.country)
    plan = run_question_plan(
        args.country,
        output_dir,
        args.index,
        args.openai_key,
        args.vector_store_id,
        args.backend,
        question_id=args.question_id,
    )
    print(json.dumps({
        'country': args.country,
        'questions': len(plan),
        'question_ids': [item['question_id'] for item in plan],
        'output_dir': output_dir,
        'datasets': ['question_run_log.csv', 'evidencias.csv', 'respostas.csv'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
