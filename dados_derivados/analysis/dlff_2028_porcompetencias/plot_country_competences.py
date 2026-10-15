#!/usr/bin/env python3
"""Generate one DLGF lexical-coverage chart per country from a run summary."""
from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


AREA_COLORS = {
    "CA0": "#4E79A7",
    "CA1": "#59A14F",
    "CA2": "#F28E2B",
    "CA3": "#E15759",
    "CA4": "#B07AA1",
    "CA5": "#76B7B2",
    "CA6": "#EDC948",
}


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Nenhuma linha encontrada em {path}.")
    required = {
        "country",
        "area_code",
        "area_name",
        "competence_code",
        "competence_name",
        "documents_in_country",
        "document_coverage_percent",
    }
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Resumo sem colunas obrigatórias: {sorted(missing)}")
    return rows


def plot_country(country: str, rows: list[dict[str, str]], output_dir: Path) -> Path:
    rows = sorted(rows, key=lambda row: tuple(int(part) for part in row["competence_code"].split(".")))
    coverage = [float(row["document_coverage_percent"]) for row in rows]
    labels = [f'{row["competence_code"]} — {row["competence_name"]}' for row in rows]
    colors = [AREA_COLORS[row["area_code"]] for row in rows]
    documents = int(rows[0]["documents_in_country"])

    figure, axis = plt.subplots(figsize=(13, 11))
    positions = list(range(len(rows)))
    axis.barh(positions, coverage, color=colors, edgecolor="white", linewidth=0.7)
    axis.set_yticks(positions, labels, fontsize=8)
    axis.invert_yaxis()
    axis.set_xlim(0, 100)
    axis.set_xlabel("Cobertura documental com indicador lexical (%)")
    axis.set_title(
        f"{country.title()} — indicadores lexicais por competência DLGF 2018\n"
        f"{documents} documento(s) nacional(is) analisado(s)"
    )
    axis.xaxis.grid(True, color="#D9D9D9", linewidth=0.8)
    axis.set_axisbelow(True)

    areas = {
        row["area_code"]: row["area_name"]
        for row in rows
    }
    legend = [
        Patch(facecolor=AREA_COLORS[code], label=f"{code} — {areas[code]}")
        for code in sorted(areas)
    ]
    axis.legend(
        handles=legend,
        title="Áreas gerais DLGF",
        loc="lower center",
        bbox_to_anchor=(0.5, -0.28),
        ncol=2,
        fontsize=8,
        title_fontsize=9,
        frameon=False,
    )
    figure.text(
        0.01,
        0.01,
        "Ocorrências são indicadores lexicais; não comprovam equivalência semântica ou curricular.",
        fontsize=8,
        color="#555555",
    )
    figure.subplots_adjust(left=0.36, right=0.97, top=0.9, bottom=0.25)

    output = output_dir / f"{slug(country)}_cobertura_competencias_dlgf.png"
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV country_competence_summary.csv da rodada.")
    parser.add_argument("--out", required=True, help="Pasta onde serão gravados os PNGs por país.")
    args = parser.parse_args()

    summary_path = Path(args.input).resolve()
    output_dir = Path(args.out).resolve()
    if not summary_path.is_file():
        raise FileNotFoundError(f"Resumo não encontrado: {summary_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    countries: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in load_rows(summary_path):
        countries[row["country"]].append(row)

    outputs = [plot_country(country, rows, output_dir) for country, rows in sorted(countries.items())]
    print(f"Gráficos gerados: {len(outputs)}")
    print(f"Resultados: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
