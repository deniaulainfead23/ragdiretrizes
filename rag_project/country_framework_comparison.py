from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def aggregate_country_framework_summary(evidence_csv: str | Path) -> list[dict[str, Any]]:
    csv_path = Path(evidence_csv)
    if not csv_path.exists():
        return []

    rows_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    with csv_path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            country = (row.get('country') or '').strip()
            framework_id = (row.get('framework_id') or '').strip()
            area_code = (row.get('area_code') or row.get('dimension_code') or '').strip()
            area_name = row.get('area_name') or row.get('dimension_name', '')
            validation_status = (row.get('validation_status') or '').strip().lower()
            if validation_status not in {'validated', 'validado', 'reformulated', 'reformulado'}:
                continue
            if not country or framework_id != 'DLGF_2018' or not area_code:
                continue

            key = (country, framework_id, area_code)
            if key not in rows_by_key:
                rows_by_key[key] = {
                    'country': country,
                    'framework_id': framework_id,
                    'area_code': area_code,
                    'area_name': area_name,
                    'evidence_count': 0,
                    'documents_with_hits': set(),
                    'status': 'evidence_found',
                }

            summary = rows_by_key[key]
            summary['evidence_count'] += 1
            doc_id = (row.get('document_id') or '').strip()
            if doc_id:
                summary['documents_with_hits'].add(doc_id)

    output: list[dict[str, Any]] = []
    for summary in rows_by_key.values():
        summary['documents_with_hits'] = sorted(summary['documents_with_hits'])
        summary['document_count'] = len(summary['documents_with_hits'])
        summary['validation_status'] = 'validated' if summary['evidence_count'] > 0 else 'not_detected'
        output.append(summary)

    output.sort(key=lambda item: (item['country'], item['framework_id'], item['area_code']))
    return output


def write_country_framework_summary(evidence_csv: str | Path, output_csv: str | Path) -> list[dict[str, Any]]:
    rows = aggregate_country_framework_summary(evidence_csv)
    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'country', 'framework_id', 'area_code', 'area_name',
        'evidence_count', 'document_count', 'validation_status', 'documents_with_hits'
    ]
    with out_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                'country': row['country'],
                'framework_id': row['framework_id'],
                'area_code': row['area_code'],
                'area_name': row['area_name'],
                'evidence_count': row['evidence_count'],
                'document_count': row['document_count'],
                'validation_status': row['validation_status'],
                'documents_with_hits': '; '.join(row['documents_with_hits']),
            })

    return rows
