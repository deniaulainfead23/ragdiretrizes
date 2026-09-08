from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from rag_project.build_dataset import extract_text_from_file
from rag_project.framework_registry import get_framework_by_id


def _normalize_text(value: str) -> str:
    return ' '.join((value or '').lower().replace('\n', ' ').replace('\r', ' ').split())


def detect_framework_hits(text: str) -> list[dict[str, Any]]:
    normalized = _normalize_text(text)
    normalized_tokens = set(normalized.split())
    framework = get_framework_by_id('UNESCO_GCED_2015') or {}
    hits: list[dict[str, Any]] = []

    for dimension in framework.get('dimensions', []):
        code = dimension.get('code')
        keywords = dimension.get('keywords', [])
        for keyword in keywords:
            phrase = _normalize_text(keyword)
            if not phrase:
                continue

            match = False
            if phrase in normalized:
                match = True
            else:
                keyword_tokens = phrase.split()
                if keyword_tokens and all(token in normalized_tokens for token in keyword_tokens):
                    match = True

            if match:
                hits.append({
                    'framework_id': 'UNESCO_GCED_2015',
                    'dimension_code': code,
                    'dimension_name': dimension.get('name'),
                    'keyword': keyword,
                    'match_type': 'phrase',
                })
    return hits


def _sanitize_csv_value(value: Any) -> str:
    text = '' if value is None else str(value)
    text = text.replace('\x00', ' ').replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    return text


def classify_evidence_record(snippet: str, framework_id: str, dimension_code: str, dimension_name: str, api_key: str | None = None, model: str = 'gpt-4o-mini') -> dict[str, Any]:
    api_key = api_key or os.environ.get('OPENAI_API_KEY')
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            prompt = (
                'Classifique este trecho curricular segundo o framework informado. '
                'Retorne apenas JSON válido com as chaves: evidence_classification, evidence_status, validation_notes. '
                'Use evidence_classification como explicit, implicit ou none. '
                'Use evidence_status como candidate ou validated. '
                'Se houver pouca certeza, prefira implicit.\n\n'
                f'framework_id: {framework_id}\n'
                f'dimension_code: {dimension_code}\n'
                f'dimension_name: {dimension_name}\n'
                f'trecho: {snippet}'
            )
            response = client.responses.create(
                model=model,
                input=prompt,
            )
            payload = response.output_text.strip()
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return {
                    'evidence_classification': parsed.get('evidence_classification', 'implicit'),
                    'evidence_status': parsed.get('evidence_status', 'candidate'),
                    'validation_notes': parsed.get('validation_notes', 'Classified by OpenAI API.'),
                }
        except Exception:
            pass

    normalized = _normalize_text(snippet)
    explicit_terms = {
        'pensamento crítico': 'explicit',
        'pensamento critico': 'explicit',
        'empatia': 'explicit',
        'participação': 'explicit',
        'participacao': 'explicit',
        'cidadania global': 'explicit',
        'global citizenship': 'explicit',
        'critical thinking': 'explicit',
        'problem solving': 'explicit',
        'resolução de problemas': 'explicit',
        'resolucao de problemas': 'explicit',
    }
    classification = 'none'
    for phrase, label in explicit_terms.items():
        if _normalize_text(phrase) in normalized:
            classification = label
            break
    if classification == 'none':
        classification = 'implicit' if normalized else 'none'

    return {
        'evidence_classification': classification,
        'evidence_status': 'validated' if classification != 'none' else 'candidate',
        'validation_notes': 'Fallback local heuristic because OpenAI API key is missing or the API call failed; human validation remains required.',
    }


def build_evidence_matrix(corpus_root: str | Path, metadata_csv: str | Path, output_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(corpus_root)
    meta_path = Path(metadata_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []

    if not meta_path.exists() or not root.exists():
        return rows

    with meta_path.open('r', encoding='utf-8', newline='') as handle:
        records = list(csv.DictReader(handle))

    for record in records:
        file_name = record.get('file_name') or record.get('relative_path')
        if not file_name:
            continue

        candidate = root / record.get('relative_path', '')
        if not candidate.exists():
            candidate = root / file_name
        if not candidate.exists():
            continue

        text = extract_text_from_file(candidate)
        if not text:
            continue
        hits = detect_framework_hits(text)

        if not hits:
            continue

        for hit in hits:
            classification = classify_evidence_record(
                snippet=text[:600],
                framework_id=hit['framework_id'],
                dimension_code=hit['dimension_code'],
                dimension_name=hit['dimension_name'],
            )
            rows.append({
                'document_id': record.get('document_id', ''),
                'country': record.get('country', ''),
                'title_original': record.get('title_original', ''),
                'framework_id': hit['framework_id'],
                'dimension_code': hit['dimension_code'],
                'dimension_name': hit['dimension_name'],
                'matched_keyword': hit['keyword'],
                'matched_text': text[:300],
                'evidence_classification': classification['evidence_classification'],
                'evidence_status': classification['evidence_status'],
                'validation_notes': classification['validation_notes'],
                'source_file': candidate.as_posix(),
            })

    with (out_dir / 'evidence_matrix.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                'document_id', 'country', 'title_original', 'framework_id', 'dimension_code', 'dimension_name',
                'matched_keyword', 'matched_text', 'evidence_classification', 'evidence_status', 'validation_notes', 'source_file'
            ],
            quoting=csv.QUOTE_MINIMAL,
            escapechar='\\',
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _sanitize_csv_value(value) for key, value in row.items()})

    return rows
