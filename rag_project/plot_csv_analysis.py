"""Gera gráficos diretamente dos CSVs de análise já produzidos."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def plot_brazil_comparison(rows: list[dict], output: Path) -> None:
    rows = [
        row for row in rows
        if (row['group_a'] == 'brasil' or row['group_b'] == 'brasil')
        and row['group_a'] != 'UNESCO'
        and row['group_b'] != 'UNESCO'
    ]
    values = []
    for row in rows:
        other = row['group_b'] if row['group_a'] == 'brasil' else row['group_a']
        values.append((other, float(row['similarity'])))
    values.sort(key=lambda item: item[1], reverse=True)
    labels, scores = zip(*values)
    fig, axis = plt.subplots(figsize=(11, 7))
    axis.barh(list(labels)[::-1], list(scores)[::-1], color='#c24b36')
    axis.set_xlim(0, 1)
    axis.set_title('Proximidade textual dos países em relação ao Brasil')
    axis.set_xlabel('Similaridade cosseno sobre TF-IDF')
    fig.tight_layout()
    fig.savefig(output / 'brazil_country_similarity.png', dpi=180)
    plt.close(fig)


def plot_brazil_unesco(rows: list[dict], output: Path) -> None:
    reference_path = output / 'country_unesco_reference.csv'
    if reference_path.exists():
        reference_rows = read_rows(reference_path)
        if reference_rows:
            values = [(row['country'], float(row['similarity_to_unesco'])) for row in reference_rows if row['country'] != 'UNESCO']
            values.sort(key=lambda item: item[1], reverse=True)
            labels, scores = zip(*values)
            fig, axis = plt.subplots(figsize=(11, 7))
            colors = ['#176b87' if label == 'brasil' else '#83a9b5' for label in labels]
            axis.barh(list(labels)[::-1], list(scores)[::-1], color=colors[::-1])
            axis.set_xlim(0, 1)
            axis.set_title('Proximidade textual dos países em relação à UNESCO')
            axis.set_xlabel('Similaridade cosseno sobre TF-IDF')
            fig.tight_layout()
            fig.savefig(output / 'country_unesco_similarity.png', dpi=180)
            plt.close(fig)
            return

    values = []
    for row in rows:
        if row['group_a'] == 'UNESCO' or row['group_b'] == 'UNESCO':
            other = row['group_b'] if row['group_a'] == 'UNESCO' else row['group_a']
            if other not in {'PISA/OECD', 'UNESCO'}:
                values.append((other, float(row['similarity'])))
    values.sort(key=lambda item: item[1], reverse=True)
    if not values:
        return
    labels, scores = zip(*values)
    fig, axis = plt.subplots(figsize=(11, 7))
    colors = ['#176b87' if label == 'brasil' else '#83a9b5' for label in labels]
    axis.barh(list(labels)[::-1], list(scores)[::-1], color=colors[::-1])
    axis.set_xlim(0, 1)
    axis.set_title('Proximidade textual dos países em relação à UNESCO')
    axis.set_xlabel('Similaridade cosseno sobre TF-IDF')
    fig.tight_layout()
    fig.savefig(output / 'country_unesco_similarity.png', dpi=180)
    plt.close(fig)


def plot_group_terms(rows: list[dict], output: Path, groups: list[str]) -> None:
    groups = [group for group in groups if group != 'UNESCO']
    selected = [row for row in rows if row['group'] in groups and int(row['rank']) <= 10]
    if not selected:
        return
    terms = sorted({row['term'] for row in selected})
    matrix = np.zeros((len(groups), len(terms)))
    for row in selected:
        matrix[groups.index(row['group']), terms.index(row['term'])] = float(row['tfidf'])
    fig, axis = plt.subplots(figsize=(max(12, len(terms) * 0.45), 5))
    image = axis.imshow(matrix, aspect='auto', cmap='YlOrRd')
    axis.set_yticks(range(len(groups)), groups)
    axis.set_xticks(range(len(terms)), terms, rotation=75, ha='right', fontsize=8)
    axis.set_title('Termos TF-IDF mais relevantes: Brasil e contexto comparado')
    fig.colorbar(image, ax=axis, label='Peso TF-IDF')
    fig.tight_layout()
    fig.savefig(output / 'brazil_unesco_terms_heatmap.png', dpi=180)
    plt.close(fig)


def generate(input_dir: str) -> None:
    output = Path(input_dir)
    similarity = read_rows(output / 'group_similarity.csv')
    tfidf = read_rows(output / 'group_tfidf.csv')
    plot_brazil_comparison(similarity, output)
    plot_brazil_unesco(similarity, output)
    plot_group_terms(tfidf, output, ['brasil', 'UNESCO'])
    print('Graficos CSV gerados em', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gera gráficos a partir dos CSVs de análise.')
    parser.add_argument('--input', default='corpus/analysis_output')
    args = parser.parse_args()
    generate(args.input)
