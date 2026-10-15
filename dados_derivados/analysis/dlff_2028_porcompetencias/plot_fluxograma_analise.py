#!/usr/bin/env python3
"""Create a visual flowchart of the exploratory DLGF analysis."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def add_box(axis, x: float, y: float, width: float, height: float, text: str, color: str) -> None:
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.3,
        edgecolor="#34495E",
        facecolor=color,
    )
    axis.add_patch(box)
    axis.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=10,
        wrap=True,
        color="#1F2933",
    )


def add_arrow(axis, start: tuple[float, float], end: tuple[float, float]) -> None:
    axis.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#52606D",
            "linewidth": 1.5,
            "mutation_scale": 14,
        },
    )


def create_flowchart(output: Path) -> None:
    figure, axis = plt.subplots(figsize=(14, 18))
    axis.set_xlim(0, 10)
    axis.set_ylim(0, 20)
    axis.axis("off")

    axis.text(
        5,
        19.45,
        "Fluxograma da análise exploratória DLGF 2018",
        ha="center",
        va="center",
        fontsize=18,
        fontweight="bold",
        color="#102A43",
    )
    axis.text(
        5,
        19.05,
        "Triagem lexical comparativa por competências e países",
        ha="center",
        va="center",
        fontsize=11,
        color="#52606D",
    )

    boxes = [
        (1.0, 17.65, 8.0, 0.85, "1. Entrada\nconteudos.jsonl\n8.099 registros de páginas", "#D9EAF7"),
        (1.0, 16.25, 8.0, 0.85, "2. Seleção da base\nUsar explicitamente o campo source_text", "#D9EAF7"),
        (1.0, 14.85, 8.0, 0.85, "3. Filtragem\nExcluir referências internacionais e registros não nacionais\n1.297 registros excluídos", "#FDECC8"),
        (1.0, 13.45, 8.0, 0.85, "4. Reunião das páginas\nAgrupar por country + document_id\n79 documentos em 22 países", "#D9EAD3"),
        (1.0, 12.05, 8.0, 0.85, "5. Codebook DLGF 2018\n26 competências específicas organizadas em CA0–CA6", "#E8DFF5"),
        (1.0, 10.65, 8.0, 0.85, "6. Normalização e busca lexical\ncasefold + remoção de acentos\nTermos e frases completos; sem inferência semântica", "#E8DFF5"),
        (1.0, 9.25, 8.0, 0.85, "7. Análise por documento × competência\nContar ocorrências, documentos com ocorrência,\npalavras e páginas correspondentes", "#D9EAD3"),
        (1.0, 7.85, 8.0, 0.85, "8. Agregação por país\nCobertura documental (%) e frequências normalizadas\n2.054 linhas documento–competência", "#D9EAD3"),
    ]

    for x, y, width, height, text, color in boxes:
        add_box(axis, x, y, width, height, text, color)
    for current, following in zip(boxes, boxes[1:]):
        add_arrow(axis, (5, current[1]), (5, following[1] + following[3]))

    add_box(
        axis,
        0.7,
        5.95,
        4.0,
        0.95,
        "9A. Saídas tabulares\nCSV de ocorrências, resumo,\nmatriz e manifesto de hashes",
        "#D9EAF7",
    )
    add_box(
        axis,
        5.3,
        5.95,
        4.0,
        0.95,
        "9B. Visualização\n22 gráficos PNG,\num por país, com 26 competências",
        "#D9EAF7",
    )
    add_arrow(axis, (3.7, 7.85), (2.7, 6.9))
    add_arrow(axis, (6.3, 7.85), (7.3, 6.9))

    add_box(
        axis,
        1.0,
        3.95,
        8.0,
        1.05,
        "10. Validação técnica\npy_compile + 5 testes de rastreabilidade + validação dos PNGs",
        "#D9EAD3",
    )
    add_arrow(axis, (2.7, 5.95), (3.7, 5.0))
    add_arrow(axis, (7.3, 5.95), (6.3, 5.0))

    add_box(
        axis,
        1.0,
        2.25,
        8.0,
        1.05,
        "11. Interpretação responsável\nIndicadores lexicais de busca; não comprovam equivalência\nsemântica, presença curricular ou desenvolvimento da competência",
        "#FDECC8",
    )
    add_arrow(axis, (5, 3.95), (5, 3.3))

    add_box(
        axis,
        1.0,
        0.55,
        8.0,
        1.05,
        "Atenção metodológica da rodada\nO codebook está em inglês e foi aplicado a source_text.\nDocumentos em outros idiomas exigem tradução validada ou codebook específico.",
        "#F8D7DA",
    )
    add_arrow(axis, (5, 2.25), (5, 1.6))

    figure.text(
        0.5,
        0.025,
        "Rodada: run_20261015_0948 | Fonte: dados_intermediarios/data/conteudos.jsonl",
        fontsize=8,
        color="#52606D",
    )
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    output = Path(__file__).with_name("fluxograma_analise_exploratoria_dlgf.png")
    create_flowchart(output)
    print(f"Fluxograma gerado: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
