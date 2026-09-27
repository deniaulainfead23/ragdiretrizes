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
from scipy.sparse import csr_matrix, vstack as sparse_vstack

STOP_WORDS = {
    'a', 'as', 'ao', 'aos', 'com', 'da', 'das', 'de', 'do', 'dos', 'e', 'em', 'na', 'nas', 'no', 'nos', 'o', 'os', 'para', 'por', 'que', 'um', 'uma',
    'and', 'are', 'for', 'from', 'in', 'is', 'of', 'on', 'or', 'the', 'to', 'with',
    'der', 'die', 'das', 'den', 'dem', 'des', 'und', 'von', 'fur', 'für',
    'des', 'les', 'une', 'dans', 'pour', 'sur', 'avec', 'est',
    'del', 'los', 'las', 'una', 'para', 'por', 'con', 'que',
}
EXCLUDED_COUNTRY_GROUPS = {'marrocos'}
DLGF_FRAMEWORK_CSV = Path(__file__).resolve().parent / 'framework' / 'unesco_dlgf_2018.csv'
DLGF_GROUP_NAME = 'UNESCO DLGF 2018'


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


def aggregate_records(records: list[dict]) -> list[dict]:
    """Combina chunks processados para evitar que documentos longos dominem o TF-IDF."""
    grouped: dict[str, dict] = {}
    for index, record in enumerate(records):
        key = str(record.get('document_id') or record.get('document') or index)
        current = grouped.get(key)
        if current is None:
            current = dict(record)
            current['_text'] = ''
            grouped[key] = current
        current['_text'] += ('\n\n' if current['_text'] else '') + record['_text']
    return list(grouped.values())


def group_name(record: dict) -> str:
    if record.get('dataset_group') == 'unesco_dlgf_2018':
        return DLGF_GROUP_NAME
    if record.get('source_scope') == 'international_reference':
        return DLGF_GROUP_NAME if str(record.get('framework_source', '')).upper() == 'DLGF_2018' else 'International reference (excluded)'
    return record.get('country') or 'Sem país'


def load_dlgf_records(path: Path = DLGF_FRAMEWORK_CSV) -> list[dict]:
    """Representa cada uma das sete áreas do DLGF 2018 como referência lexical."""
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        areas = list(csv.DictReader(handle))
    records = []
    for area in areas:
        code = str(area.get('code', '')).strip()
        name = str(area.get('name', '')).strip()
        keywords = [term.strip() for term in str(area.get('keywords', '')).split(';') if term.strip()]
        records.append({
            'document_id': f'DLGF_2018_AREA_{code}',
            'document_title': name,
            'country': '',
            'dataset_group': 'unesco_dlgf_2018',
            'source_scope': 'international_reference',
            'framework_source': 'DLGF_2018',
            'area_code': code,
            'area_name': name,
            '_text': ' '.join([name, *keywords]),
        })
    if len(records) != 7:
        raise ValueError(f'O arquivo DLGF 2018 deve conter sete áreas; encontradas {len(records)} em {path}')
    return records


def is_excluded_country(name: str) -> bool:
    return normalized_country_name(name) in EXCLUDED_COUNTRY_GROUPS


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


def analyze(input_path: str, output_dir: str, text_field: str = 'english_text', top_n: int = 20) -> None:
    country_records = [
        record for record in load_records(Path(input_path), text_field)
        if record.get('country') and not is_excluded_country(record.get('country', ''))
        and record.get('source_scope', 'national') != 'international_reference'
    ]
    records = aggregate_records(country_records + load_dlgf_records())
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    document_names = [
        f"{group_name(record)}/{record.get('document_title') or record.get('document') or record.get('document_id', '')}"
        for record in records
    ]
    document_texts = [record['_text'] for record in records]
    vectorizer_args = dict(lowercase=True, strip_accents='unicode', ngram_range=(1, 2), min_df=2, max_df=0.98, max_features=10000, sublinear_tf=True, dtype=np.float32, stop_words=sorted(STOP_WORDS), token_pattern=r'(?u)\b\w{3,}\b')
    vectorizer = TfidfVectorizer(**vectorizer_args)
    try:
        document_matrix = vectorizer.fit_transform(document_texts)
    except ValueError as exc:
        if 'empty vocabulary' not in str(exc).lower() and 'no terms remain' not in str(exc).lower():
            raise
        vectorizer_args.update(min_df=1, max_df=1.0)
        vectorizer = TfidfVectorizer(**vectorizer_args)
        document_matrix = vectorizer.fit_transform(document_texts)
    terms = vectorizer.get_feature_names_out()

    document_rows = []
    for row_index, document_name in enumerate(document_names):
        values = document_matrix[row_index].toarray().ravel()
        for term_index in np.flatnonzero(values):
            document_rows.append({'document': document_name, 'country': records[row_index].get('country', ''), 'term': terms[term_index], 'tfidf': round(float(values[term_index]), 8)})
    write_rows(output / 'lexical_document_tfidf.csv', ['document', 'country', 'term', 'tfidf'], document_rows)
    write_rows(output / 'lexical_document_top_terms.csv', ['group', 'rank', 'term', 'tfidf'], top_terms(document_matrix, document_names, terms, top_n))

    grouped_indexes: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        grouped_indexes[group_name(record)].append(index)
    group_names = sorted(grouped_indexes)
    country_group_names = [name for name in group_names if name != DLGF_GROUP_NAME and not is_excluded_country(name)]
    country_group_matrix = sparse_vstack([
        csr_matrix(document_matrix[grouped_indexes[name]].mean(axis=0))
        for name in country_group_names
    ])
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

    dlgf_records = load_dlgf_records()
    dlgf_doc_rows = {
        str(records[index].get('document_id')): index
        for index in range(len(records))
        if records[index].get('dataset_group') == 'unesco_dlgf_2018'
    }
    dlgf_rows = []
    country_area_matrix = []
    for country in country_group_names:
        country_vector = csr_matrix(document_matrix[grouped_indexes[country]].mean(axis=0))
        area_scores = {'country': country}
        for area in dlgf_records:
            area_index = dlgf_doc_rows[area['document_id']]
            similarity = float(cosine_similarity(country_vector, document_matrix[area_index])[0, 0])
            dlgf_rows.append({
                'country': country,
                'framework_id': 'DLGF_2018',
                'area_code': area['area_code'],
                'area_name': area['area_name'],
                'lexical_similarity': round(similarity, 8),
                'interpretation_limit': 'Pista exploratória de vocabulário; não prova equivalência nem adesão curricular.',
            })
            area_scores[f"area_{area['area_code']}"] = round(similarity, 8)
        country_area_matrix.append(area_scores)
    write_rows(output / 'country_dlgf_area_similarity.csv',
               ['country', 'framework_id', 'area_code', 'area_name', 'lexical_similarity', 'interpretation_limit'], dlgf_rows)
    write_rows(output / 'country_dlgf_area_similarity_matrix.csv',
               ['country'] + [f'area_{code}' for code in range(7)], country_area_matrix)
    if country_area_matrix:
        area_columns = [f'area_{code}' for code in range(7)]
        heatmap = np.array([[row[column] for column in area_columns] for row in country_area_matrix], dtype=float)
        fig, axis = plt.subplots(figsize=(12, max(5, len(country_area_matrix) * 0.42)))
        image = axis.imshow(heatmap, cmap='YlGnBu', vmin=0, vmax=1, aspect='auto')
        axis.set_xticks(range(7), [f"Área {area['area_code']}\n{area['area_name']}" for area in dlgf_records], fontsize=8)
        axis.set_yticks(range(len(country_area_matrix)), [row['country'] for row in country_area_matrix], fontsize=8)
        axis.set_title('Proximidade lexical exploratória com as áreas do UNESCO DLGF 2018')
        fig.colorbar(image, ax=axis, label='Similaridade cosseno TF-IDF')
        fig.tight_layout()
        fig.savefig(output / 'country_dlgf_area_similarity_heatmap.png', dpi=180)
        plt.close(fig)

    country_rows = [row for row in country_group_rows if row['group'] != DLGF_GROUP_NAME]
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
        'country_groups': country_group_names,
        'benchmark_groups': [name for name in group_names if name not in country_group_names],
        'framework_reference': 'DLGF_2018',
        'framework_area_count': len(dlgf_records),
        'analysis_mode': 'exploratory_lexical',
        'method_note': (
            'As métricas de similaridade textual e TF-IDF são empregadas como ferramentas exploratórias que indicam pistas de vocabulário e proximidade de termos, não devendo ser lidas como prova direta de equivalência curricular. '
            'A referência internacional exclusiva desta análise é o UNESCO DLGF 2018, representado pelas sete áreas e seus termos do CSV oficial do projeto. '
            'A entrada usa documentos nacionais agregados por document_id; a similaridade de país-área usa a média dos vetores documentais. '
            'A análise lexical entre idiomas exige dataset com tradução consistente para um idioma comum.'
        ),
    }
    (output / 'analysis_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gera TF-IDF, similaridade e gráficos do dataset JSONL.')
    parser.add_argument('--input', default='dados_intermediarios/data/conteudos.jsonl')
    parser.add_argument('--out', default='dados_intermediarios/analise_lexical')
    parser.add_argument('--text-field', default='source_text', choices=['english_text', 'source_text'])
    parser.add_argument('--top-n', type=int, default=20)
    args = parser.parse_args()
    analyze(args.input, args.out, args.text_field, args.top_n)
