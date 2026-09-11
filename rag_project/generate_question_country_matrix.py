from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch


STATUS_COLORS = {
    'candidate': '#F2C14E',
    'validated': '#43AA8B',
    'partially_validated': '#F9844A',
    'not_confirmed': '#F94144',
    'rejected': '#6C757D',
}
STATUS_LABELS = {
    'candidate': 'Candidata à validação',
    'validated': 'Validada',
    'partially_validated': 'Parcialmente validada',
    'not_confirmed': 'Não confirmada',
    'rejected': 'Rejeitada',
}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def create_matrix(input_path: Path, output_path: Path) -> None:
    rows = load_rows(input_path)
    countries = sorted({row['country'] for row in rows})
    questions = sorted({row['question_id'] for row in rows})
    values = {(row['country'], row['question_id']): row.get('situacao_resposta', 'candidate') for row in rows}
    counts = Counter(values.values())

    fig_height = max(8, len(countries) * 0.38 + 3.6)
    fig, (axis, summary_axis) = plt.subplots(
        1, 2, figsize=(15, fig_height), gridspec_kw={'width_ratios': [4.6, 1.6]}
    )
    axis.set_xlim(-0.5, len(questions) - 0.5)
    axis.set_ylim(len(countries) - 0.5, -0.5)
    axis.set_xticks(range(len(questions)), questions, fontsize=11, fontweight='bold')
    axis.set_yticks(range(len(countries)), countries, fontsize=9)
    axis.set_xlabel('Código da pergunta', fontsize=11, labelpad=10)
    axis.set_ylabel('País', fontsize=11, labelpad=10)
    axis.set_title('Matriz de perguntas, países e situação das respostas', fontsize=15, fontweight='bold', pad=16)
    axis.set_facecolor('#F7F4EF')
    axis.grid(True, color='white', linewidth=2)

    for y, country in enumerate(countries):
        for x, question in enumerate(questions):
            status = values.get((country, question))
            if status is None:
                axis.scatter(x, y, s=310, marker='s', color='#E0DDD6', edgecolor='white', linewidth=1.5)
                axis.text(x, y, '—', ha='center', va='center', color='#77716A', fontsize=11)
            else:
                axis.scatter(x, y, s=310, marker='s', color=STATUS_COLORS.get(status, '#B8B8B8'), edgecolor='white', linewidth=1.5)
                axis.text(x, y, status[:1].upper(), ha='center', va='center', color='#263238', fontsize=10, fontweight='bold')

    summary_axis.axis('off')
    summary_axis.set_title('Resumo atual', fontsize=13, fontweight='bold', pad=16)
    summary_axis.text(0.02, 0.92, f'Países: {len(countries)}\nPerguntas: {len(questions)}\nRespostas: {len(rows)}', transform=summary_axis.transAxes, va='top', fontsize=12, linespacing=1.6)
    summary_axis.text(0.02, 0.72, 'Situação', transform=summary_axis.transAxes, va='top', fontsize=11, fontweight='bold')
    y = 0.66
    for status in sorted(counts):
        summary_axis.scatter(0.06, y, s=150, marker='s', color=STATUS_COLORS.get(status, '#B8B8B8'), transform=summary_axis.transAxes, clip_on=False)
        summary_axis.text(0.13, y, f'{STATUS_LABELS.get(status, status)}: {counts[status]}', transform=summary_axis.transAxes, va='center', fontsize=10)
        y -= 0.075
    summary_axis.text(0.02, 0.40, 'Nota', transform=summary_axis.transAxes, va='top', fontsize=11, fontweight='bold')
    summary_axis.text(0.02, 0.35, 'Todas as respostas\nestão como\n“candidate” e\nainda aguardam\nvalidação.', transform=summary_axis.transAxes, va='top', fontsize=10, linespacing=1.55)

    legend_items = [Patch(facecolor=color, label=f'{STATUS_LABELS.get(status, status)} ({status[:1].upper()})') for status, color in STATUS_COLORS.items() if status in counts]
    fig.legend(handles=legend_items, loc='lower center', ncol=min(4, len(legend_items)), frameon=False, bbox_to_anchor=(0.5, 0.01), fontsize=10)
    fig.text(0.5, 0.035, 'Células sem pergunta aplicável aparecem como “—”. A letra dentro da célula identifica a situação.', ha='center', fontsize=9, color='#5B554F')
    fig.patch.set_facecolor('#FFFCF7')
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description='Gera uma matriz visual das respostas por país e pergunta.')
    parser.add_argument('--input', default='analysis/consolidado/respostas_consolidadas.csv')
    parser.add_argument('--output', default='analysis/consolidado/matriz_perguntas_paises.png')
    args = parser.parse_args()
    create_matrix(Path(args.input), Path(args.output))
    print(args.output)


if __name__ == '__main__':
    main()