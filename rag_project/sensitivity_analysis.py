from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _read_similarity_values(path: Path) -> list[float]:
    if not path.exists():
        return []
    values: list[float] = []
    with path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            value = (row.get('similarity') or '').strip()
            if value:
                try:
                    values.append(float(value))
                except ValueError:
                    continue
    return values


def build_sensitivity_report(input_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    source_dir = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    baseline_summary = {}
    summary_path = source_dir / 'analysis_summary.json'
    if summary_path.exists():
        try:
            baseline_summary = json.loads(summary_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            baseline_summary = {}

    similarity_csv = source_dir / 'lexical_group_similarity.csv'
    values = _read_similarity_values(similarity_csv)
    mean_similarity = sum(values) / len(values) if values else 0.0

    runs = [{
        'label': 'baseline',
        'input_dir': str(source_dir),
        'files_checked': ['analysis_summary.json', 'lexical_group_similarity.csv'],
        'similarity_values': values,
        'mean_similarity': round(mean_similarity, 6),
        'analysis_mode': baseline_summary.get('analysis_mode', 'exploratory_lexical'),
        'method_note': baseline_summary.get('method_note', 'TLexical analysis used as exploratory evidence only.'),
    }]

    with (output_path / 'sensitivity_results.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['label', 'input_dir', 'analysis_mode', 'mean_similarity', 'method_note'])
        writer.writeheader()
        for run in runs:
            writer.writerow({
                'label': run['label'],
                'input_dir': run['input_dir'],
                'analysis_mode': run['analysis_mode'],
                'mean_similarity': run['mean_similarity'],
                'method_note': run['method_note'],
            })

    summary_md = f"""# Sensitivity summary

## Run baseline
- Analysis mode: {runs[0]['analysis_mode']}
- Mean similarity (lexical): {runs[0]['mean_similarity']:.6f}
- Samples: {len(runs[0]['similarity_values'])}
- Interpretation: this result is exploratory and should not be interpreted as curricular equivalence or definitive alignment.

## Methodological note
{runs[0]['method_note']}
"""
    (output_path / 'sensitivity_summary.md').write_text(summary_md, encoding='utf-8')

    return {
        'runs': runs,
        'mean_similarity': mean_similarity,
        'source_dir': str(source_dir),
        'output_dir': str(output_path),
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Build a lightweight sensitivity report for the lexical analysis.')
    parser.add_argument('--input-dir', default='corpus/analysis_output')
    parser.add_argument('--output-dir', default='corpus/analysis_output')
    args = parser.parse_args()
    report = build_sensitivity_report(args.input_dir, args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
