#!/usr/bin/env python3
"""Generate a direct country-by-competence coverage heatmap."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_matrix(path: Path) -> tuple[list[str], list[str], np.ndarray, list[int]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Matriz vazia: {path}")
    features = [field for field in rows[0] if field not in {"country", "documents_in_country"}]
    rows.sort(key=lambda row: row["country"])
    countries = [row["country"] for row in rows]
    documents = [int(float(row["documents_in_country"])) for row in rows]
    values = np.array([[float(row[field]) for field in features] for row in rows])
    return countries, features, values, documents


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    countries, features, values, documents = load_matrix(Path(args.input).resolve())
    output = Path(args.out).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(18, 11))
    image = axis.imshow(values, aspect="auto", cmap="YlGnBu", vmin=0, vmax=100)
    axis.set_xticks(range(len(features)), features, rotation=60, ha="left", fontsize=9)
    axis.set_yticks(
        range(len(countries)),
        [f"{country} (n={documents[index]})" for index, country in enumerate(countries)],
        fontsize=9,
    )
    axis.set_xlabel("Competências específicas DLGF 2018")
    axis.set_ylabel("País e número de documentos analisados")
    axis.set_title("Cobertura documental de indicadores lexicais por país e competência")
    colorbar = figure.colorbar(image, ax=axis, pad=0.02)
    colorbar.set_label("Percentual de documentos do país com indicador lexical")
    axis.set_xticks(np.arange(-0.5, len(features), 1), minor=True)
    axis.set_yticks(np.arange(-0.5, len(countries), 1), minor=True)
    axis.grid(which="minor", color="white", linewidth=0.7)
    axis.tick_params(which="minor", bottom=False, left=False)
    figure.text(
        0.01,
        0.01,
        "Leitura descritiva da matriz; não é ranking de países nem medida de equivalência curricular.",
        fontsize=8,
        color="#52606D",
    )
    figure.tight_layout()
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    print(f"Mapa de calor gerado: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
