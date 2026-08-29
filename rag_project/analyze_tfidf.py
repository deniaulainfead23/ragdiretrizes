"""Calcula TF-IDF, similaridade entre grupos e gráficos do corpus."""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STOP_WORDS = {
    'a', 'as', 'ao', 'aos', 'com', 'da', 'das', 'de', 'do', 'dos', 'e', 'em', 'na', 'nas', 'no', 'nos', 'o', 'os', 'para', 'por', 'que', 'um', 'uma',
    'and', 'are', 'for', 'from', 'in', 'is', 'of', 'on', 'or', 'the', 'to', 'with',
    'der', 'die', 'das', 'den', 'dem', 'des', 'und', 'von', 'fur', 'für',
    'des', 'les', 'une', 'dans', 'pour', 'sur', 'avec', 'est',
    'del', 'los', 'las', 'una', 'para', 'por', 'con', 'que',
}


def load_records(path: Path, text_field: str) -> list[dict]:
    records = []
    fallback_fields = [text_field, 'english_text', 'source_text']
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            text = ''
            for field in fallback_fields:
                candidate = (record.get(field) or '').strip()
                if candidate:
                    text = candidate
                    break
            if text:
                record['_text'] = text
                records.append(record)
    if not records:
        raise ValueError(f'Nenhum texto encontrado em {path} usando {text_field!r}')
    return records


def group_name(record: dict) -> str:
    if record.get('dataset_group') == 'unesco':
        return 'UNESCO'
    if record.get('dataset_group') == 'pisa':
        return 'PISA/OECD'
    return record.get('country') or 'Sem país'


def normalized_country_name(value: str) -> str:
    value = unicodedata.normalize('NFKD', value.lower()).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')


def frequency_rows(records: list[dict]) -> list[dict]:
    counters = defaultdict(Counter)
    for record in records:
        group = group_name(record)
        counters[group].update(re.findall(r"(?u)\b[A-Za-zÀ-ÖØ-öø-ÿ]{3,}\b", record['_text'].lower()))
    rows = []
    for group, counter in sorted(counters.items()):
        for rank, (term, frequency) in enumerate(counter.most_common(50), start=1):
            if term in STOP_WORDS:
                continue
            rows.append({'group': group, 'rank': rank, 'term': term, 'frequency': frequency})
    return rows


def write_rows(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def top_terms(matrix, names: list[str], terms: np.ndarray, limit: int = 20) -> list[dict]:
    rows = []
    for row_index, name in enumerate(names):
        scores = matrix[row_index].toarray().ravel()
        indexes = np.argsort(scores)[::-1]
        for rank, term_index in enumerate(indexes[:limit], start=1):
            if scores[term_index] <= 0:
                continue
            rows.append({'group': name, 'rank': rank, 'term': terms[term_index], 'tfidf': round(float(scores[term_index]), 8)})
    return rows


def plot_top_terms(country_rows: list[dict], output: Path) -> None:
    totals = defaultdict(float)
    for row in country_rows:
        if row['rank'] <= 10 and re.fullmatch(r'[A-Za-zÀ-ÖØ-öø-ÿ]+(?: [A-Za-zÀ-ÖØ-öø-ÿ]+)?', row['term']):
            totals[row['term']] += float(row['tfidf'])
    selected = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:15]
    if not selected:
        return
    labels, values = zip(*selected)
    fig, axis = plt.subplots(figsize=(12, 7))
    axis.barh(list(labels)[::-1], list(values)[::-1], color='#176b87')
    axis.set_title('Termos mais relevantes nos grupos nacionais')
    axis.set_xlabel('Soma dos pesos TF-IDF entre os 10 primeiros termos de cada grupo')
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_heatmap(similarity: np.ndarray, names: list[str], output: Path) -> None:
    size = max(8, min(18, len(names) * 0.65))
    fig, axis = plt.subplots(figsize=(size, size * 0.82))
    image = axis.imshow(similarity, cmap='YlGnBu', vmin=0, vmax=1)
    axis.set_xticks(range(len(names)), names, rotation=75, ha='right', fontsize=8)
    axis.set_yticks(range(len(names)), names, fontsize=8)
    axis.set_title('Similaridade textual entre grupos (cosseno sobre TF-IDF)')
    fig.colorbar(image, ax=axis, label='Similaridade')
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def write_pisa_comparison(output: Path, group_names: list[str], similarity: np.ndarray, pisa_path: Path) -> None:
    if not pisa_path.exists() or 'UNESCO' not in group_names:
        return
    pisa_rows = list(csv.DictReader(pisa_path.open(encoding='utf-8', newline='')))
    unesco_index = group_names.index('UNESCO')
    similarity_by_group = {normalized_country_name(name): float(similarity[index, unesco_index]) for index, name in enumerate(group_names) if name not in {'UNESCO', 'PISA/OECD'}}
    rows = []
    for row in pisa_rows:
        country = row['country']
        group = normalized_country_name(country)
        rows.append({
            'country': country,
            'continent': row['continent'],
            'pisa_2022_aggregate': row['pisa_2022_aggregate'],
            'similarity_to_unesco': round(similarity_by_group.get(group, float('nan')), 8),
            'selection_criterion': row['selection_criterion'],
        })
    write_rows(output / 'pisa_unesco_comparison.csv', ['country', 'continent', 'pisa_2022_aggregate', 'similarity_to_unesco', 'selection_criterion'], rows)


def plot_pisa_comparison(output: Path) -> None:
    path = output / 'pisa_unesco_comparison.csv'
    rows = list(csv.DictReader(path.open(encoding='utf-8', newline=''))) if path.exists() else []
    points = [(float(row['pisa_2022_aggregate']), float(row['similarity_to_unesco']), row['country']) for row in rows if row['pisa_2022_aggregate'] and row['similarity_to_unesco'] not in {'', 'nan'}]
    if not points:
        return
    x, y, labels = zip(*points)
    fig, axis = plt.subplots(figsize=(10, 7))
    axis.scatter(x, y, color='#c24b36', alpha=0.85)
    for point_x, point_y, label in points:
        axis.annotate(label, (point_x, point_y), fontsize=8, xytext=(4, 4), textcoords='offset points')
    axis.set_title('PISA 2022 e proximidade textual com UNESCO')
    axis.set_xlabel('Escore agregado informado no Quadro 2')
    axis.set_ylabel('Similaridade cosseno com UNESCO')
    fig.tight_layout()
    fig.savefig(output / 'pisa_vs_unesco_similarity.png', dpi=180)
    plt.close(fig)


def analyze(input_path: str, output_dir: str, text_field: str = 'english_text', top_n: int = 20) -> None:
    records = load_records(Path(input_path), text_field)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    document_names = [f"{record.get('country', '')}/{record.get('document', '')}" for record in records]
    document_texts = [record['_text'] for record in records]
    vectorizer = TfidfVectorizer(lowercase=True, strip_accents='unicode', ngram_range=(1, 2), min_df=2, max_df=0.98, max_features=10000, sublinear_tf=True, stop_words=sorted(STOP_WORDS), token_pattern=r'(?u)\b\w{3,}\b')
    document_matrix = vectorizer.fit_transform(document_texts)
    terms = vectorizer.get_feature_names_out()

    document_rows = []
    for row_index, document_name in enumerate(document_names):
        values = document_matrix[row_index].toarray().ravel()
        for term_index in np.flatnonzero(values):
            document_rows.append({'document': document_name, 'country': records[row_index].get('country', ''), 'term': terms[term_index], 'tfidf': round(float(values[term_index]), 8)})
    write_rows(output / 'lexical_document_tfidf.csv', ['document', 'country', 'term', 'tfidf'], document_rows)
    write_rows(output / 'lexical_document_top_terms.csv', ['group', 'rank', 'term', 'tfidf'], top_terms(document_matrix, document_names, terms, top_n))

    grouped_texts = defaultdict(list)
    for record in records:
        grouped_texts[group_name(record)].append(record['_text'])
    group_names = sorted(grouped_texts)
    country_group_names = [name for name in group_names if name not in {'UNESCO', 'PISA/OECD'}]
    country_group_matrix = vectorizer.transform(['\n'.join(grouped_texts[name]) for name in country_group_names])
    country_group_rows = []
    for row in top_terms(country_group_matrix, country_group_names, terms, top_n):
        country_group_rows.append(row)
    write_rows(output / 'lexical_group_tfidf.csv', ['group', 'rank', 'term', 'tfidf'], country_group_rows)
    write_rows(output / 'lexical_group_frequency.csv', ['group', 'rank', 'term', 'frequency'], frequency_rows(records))

    country_similarity = cosine_similarity(country_group_matrix)
    write_rows(output / 'lexical_group_similarity.csv', ['group_a', 'group_b', 'similarity'], [
        {'group_a': country_group_names[i], 'group_b': country_group_names[j], 'similarity': round(float(country_similarity[i, j]), 8)}
        for i in range(len(country_group_names)) for j in range(i + 1, len(country_group_names))
    ])
    with (output / 'lexical_group_similarity_matrix.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['group'] + country_group_names)
        for name, row in zip(country_group_names, country_similarity):
            writer.writerow([name] + [round(float(value), 8) for value in row])

    full_group_matrix = vectorizer.transform(['\n'.join(grouped_texts[name]) for name in group_names])
    full_similarity = cosine_similarity(full_group_matrix)

    if 'brasil' in country_group_names and 'UNESCO' in group_names:
        unesco_index = group_names.index('UNESCO')
        ranking = []
        for index, name in enumerate(country_group_names):
            country_index = group_names.index(name)
            ranking.append({'country': name, 'similarity_to_unesco': round(float(full_similarity[country_index, unesco_index]), 8), 'similarity_to_brazil': round(float(country_similarity[index, country_group_names.index('brasil')]), 8)})
        ranking.sort(key=lambda row: row['similarity_to_unesco'], reverse=True)
        write_rows(output / 'lexical_country_similarity_ranking.csv', ['country', 'similarity_to_unesco', 'similarity_to_brazil'], ranking)
        reference_rows = [
            {'country': name, 'similarity_to_unesco': round(float(full_similarity[group_names.index(name), unesco_index]), 8)}
            for name in country_group_names
        ]
        write_rows(output / 'country_unesco_reference.csv', ['country', 'similarity_to_unesco'], reference_rows)
    write_pisa_comparison(output, group_names, full_similarity, Path('corpus/pisa/pisa_2022_selection.csv'))
    plot_pisa_comparison(output)

    country_rows = [row for row in country_group_rows if row['group'] != 'UNESCO']
    plot_top_terms(country_rows, output / 'lexical_top_terms_groups.png')
    plot_heatmap(country_similarity, country_group_names, output / 'lexical_group_similarity_heatmap.png')

    legacy_aliases = {
        'lexical_document_tfidf.csv': 'document_tfidf.csv',
        'lexical_document_top_terms.csv': 'document_top_terms.csv',
        'lexical_group_tfidf.csv': 'group_tfidf.csv',
        'lexical_group_frequency.csv': 'group_frequency.csv',
        'lexical_group_similarity.csv': 'group_similarity.csv',
        'lexical_group_similarity_matrix.csv': 'group_similarity_matrix.csv',
        'lexical_country_similarity_ranking.csv': 'country_similarity_ranking.csv',
        'lexical_top_terms_groups.png': 'top_terms_groups.png',
        'lexical_group_similarity_heatmap.png': 'group_similarity_heatmap.png',
    }
    for lexical_name, legacy_name in legacy_aliases.items():
        source = output / lexical_name
        target = output / legacy_name
        if source.exists() and source != target:
            target.write_bytes(source.read_bytes())

    summary = {
        'input': str(input_path), 'text_field': text_field, 'documents': len(records),
        'groups': group_names, 'vocabulary_size': len(terms),
        'unesco_included': 'UNESCO' in group_names,
        'analysis_mode': 'exploratory_lexical',
        'method_note': 'TF-IDF e similaridade são exploratórios e não equivalem a avaliação documental nem a alinhamento curricular.',
    }
    (output / 'analysis_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gera TF-IDF, similaridade e gráficos do dataset JSONL.')
    parser.add_argument('--input', default='corpus/dataset_output/dataset_english.jsonl')
    parser.add_argument('--out', default='corpus/analysis_output')
    parser.add_argument('--text-field', default='english_text', choices=['english_text', 'source_text'])
    parser.add_argument('--top-n', type=int, default=20)
    args = parser.parse_args()
    analyze(args.input, args.out, args.text_field, args.top_n)
