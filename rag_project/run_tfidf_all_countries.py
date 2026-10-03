from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv

from rag_project.analyze_tfidf import STOP_WORDS, analyze_within_country
from rag_project.paths import INTERMEDIATE_DATA_DIR, LEXICAL_ANALYSIS_DIR, ROOT
from rag_project.run_curated_pipeline import build_english_page_dataset

DEFAULT_RUN_ID = "todos_paises_exploratorio_20260927_01"
TRANSLATION_MODEL = "gpt-4o-mini"
COUNTRY_LABELS = {
    "africa-do-sul": "África do Sul", "australia": "Austrália", "brasil": "Brasil",
    "canada": "Canadá", "chile": "Chile", "china": "China",
    "coreia-do-sul": "Coreia do Sul", "estonia": "Estônia", "eua": "Estados Unidos",
    "finlandia": "Finlândia", "gana": "Gana", "hong-kong": "Hong Kong",
    "irlanda": "Irlanda", "japao": "Japão", "nova-zelandia": "Nova Zelândia",
    "quenia": "Quênia", "reino-unido": "Reino Unido", "ruanda": "Ruanda",
    "singapura": "Singapura", "suica": "Suíça", "taiwan": "Taiwan", "uruguai": "Uruguai",
}


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL inválido em {path}, linha {line_number}.") from exc


def verify_translation_coverage(source_dataset: Path, translated_dataset: Path) -> dict[str, Any]:
    source_pages: dict[str, str] = {}
    source_counts: Counter[str] = Counter()
    for record in _iter_jsonl(source_dataset):
        content_id = str(record.get("content_id") or "").strip()
        country = str(record.get("country") or "").strip()
        if not content_id or not country:
            raise ValueError("Dataset original contém página sem content_id ou país.")
        if content_id in source_pages:
            raise ValueError(f"content_id duplicado no dataset original: {content_id}")
        source_pages[content_id] = country
        source_counts[country] += 1
    if not source_pages:
        raise ValueError("Dataset original não contém páginas.")

    translated_pages: set[str] = set()
    translated_segments: Counter[str] = Counter()
    translated_counts: Counter[str] = Counter()
    for record in _iter_jsonl(translated_dataset):
        page_id = str(record.get("page_content_id") or "").strip()
        country = str(record.get("country") or "").strip()
        english_text = str(record.get("english_text") or record.get("source_text") or "").strip()
        if not page_id or not country or not english_text:
            raise ValueError("Dataset traduzido contém segmento sem página, país ou texto em inglês.")
        if record.get("translation_status") != "translated" or record.get("language") != "en":
            raise ValueError(f"Segmento sem tradução inglesa confirmada para a página {page_id}.")
        if page_id not in source_pages:
            raise ValueError(f"Dataset traduzido contém página que não existe na origem: {page_id}")
        if source_pages[page_id] != country:
            raise ValueError(f"País divergente para a página traduzida {page_id}.")
        translated_pages.add(page_id)
        translated_segments[country] += 1

    missing_pages = set(source_pages) - translated_pages
    if missing_pages:
        missing_countries = Counter(source_pages[page_id] for page_id in missing_pages)
        raise ValueError(
            f"Tradução incompleta: {len(missing_pages)} páginas sem segmento traduzido; "
            f"por país: {dict(sorted(missing_countries.items()))}."
        )

    for page_id in translated_pages:
        translated_counts[source_pages[page_id]] += 1
    if set(source_counts) != set(translated_segments):
        raise ValueError("Os países da origem e do dataset traduzido não coincidem.")

    return {
        "source_pages": len(source_pages),
        "translated_pages": len(translated_pages),
        "translated_segments": sum(translated_segments.values()),
        "countries": sorted(source_counts),
        "source_pages_by_country": dict(sorted(source_counts.items())),
        "translated_pages_by_country": dict(sorted(translated_counts.items())),
        "translated_segments_by_country": dict(sorted(translated_segments.items())),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _partial_dataset_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "segments": 0, "countries": []}
    countries: Counter[str] = Counter()
    segments = 0
    for record in _iter_jsonl(path):
        segments += 1
        countries[str(record.get("country") or "unknown")] += 1
    return {"exists": True, "segments": segments, "segments_by_country": dict(sorted(countries.items()))}


def generate_tfidf_charts(analysis_dir: Path) -> dict[str, Any]:
    with (analysis_dir / "country_profiles.csv").open("r", encoding="utf-8", newline="") as handle:
        profiles = list(csv.DictReader(handle))
    terms_by_country: dict[str, list[dict[str, str]]] = {}
    with (analysis_dir / "country_local_top_terms.csv").open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["rank_within_country"]) <= 3:
                terms_by_country.setdefault(row["country"], []).append(row)

    chart_dir = analysis_dir / "countries"
    chart_dir.mkdir(parents=True, exist_ok=True)
    columns = 4
    rows_count = (len(profiles) + columns - 1) // columns
    figure, axes = plt.subplots(rows_count, columns, figsize=(16, rows_count * 2.7), squeeze=False)
    for index, profile in enumerate(profiles):
        country = profile["country"]
        country_terms = sorted(terms_by_country.get(country, []), key=lambda item: int(item["rank_within_country"]))
        axis = axes[index // columns][index % columns]
        single_document = profile.get("analysis_status") == "single_document_no_idf_contrast"
        if country_terms:
            terms = [item["term"] for item in country_terms]
            scores = [float(item["mean_tfidf_within_country"]) for item in country_terms]
            axis.barh(terms[::-1], scores[::-1], color="#176b87")
            axis.set_xlim(0, max(scores) * 1.3)
            axis.set_xlabel("Peso TF-IDF local", fontsize=7)
            axis.grid(axis="x", alpha=0.2)
        else:
            axis.text(0.5, 0.5, "Sem contraste TF-IDF\n(um documento)", ha="center", va="center", transform=axis.transAxes, fontsize=9)
            axis.set_xticks([])
            axis.set_yticks([])
        title_suffix = " | 1 doc; sem contraste IDF" if single_document else " | escala local"
        axis.set_title(f"{COUNTRY_LABELS.get(country, country)}{title_suffix}", fontsize=9)
        axis.tick_params(axis="y", labelsize=8)
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)

        country_figure, country_axis = plt.subplots(figsize=(8, 4.5))
        if country_terms:
            country_axis.barh(terms[::-1], scores[::-1], color="#176b87")
            country_axis.set_xlim(0, max(scores) * 1.3)
            country_axis.set_xlabel(
                "Peso TF-IDF local; IDF=1 com um documento"
                if single_document else "Peso TF-IDF local; não comparar com outros países"
            )
            country_axis.grid(axis="x", alpha=0.2)
        else:
            country_axis.text(0.5, 0.5, "Sem contraste TF-IDF: há apenas um documento.", ha="center", va="center", transform=country_axis.transAxes)
            country_axis.set_xticks([])
            country_axis.set_yticks([])
        country_axis.set_title(f"Top termos TF-IDF | {COUNTRY_LABELS.get(country, country)}{title_suffix}")
        country_figure.tight_layout()
        country_figure.savefig(chart_dir / f"{country}_tfidf_top3.png", dpi=180)
        plt.close(country_figure)

    for index in range(len(profiles), rows_count * columns):
        axes[index // columns][index % columns].set_visible(False)
    figure.suptitle("TF-IDF intrapaís: três termos de maior peso por país\nCada painel usa escala própria; pesos não são comparáveis entre países", fontsize=14)
    figure.tight_layout(rect=(0, 0, 1, 0.96))
    combined_path = analysis_dir / "top3_terms_by_country.png"
    figure.savefig(combined_path, dpi=180)
    plt.close(figure)
    return {
        "combined_chart": str(combined_path),
        "country_chart_dir": str(chart_dir),
        "country_charts": len(profiles),
        "countries_without_idf_contrast": [
            profile["country"] for profile in profiles
            if profile.get("analysis_status") == "single_document_no_idf_contrast"
        ],
        "countries_without_terms": [
            profile["country"] for profile in profiles if not terms_by_country.get(profile["country"])
        ],
    }


def export_tfidf_chart_assets(
    chart_report: dict[str, Any],
    output_dir: Path,
    asset_root: Path | None = None,
) -> dict[str, Any]:
    asset_dir = (asset_root or ROOT / "assets") / output_dir.name
    country_asset_dir = asset_dir / "countries"
    asset_dir.mkdir(parents=True, exist_ok=False)
    country_asset_dir.mkdir()
    combined_asset = asset_dir / "top3_terms_by_country.png"
    shutil.copy2(chart_report["combined_chart"], combined_asset)
    for chart_path in Path(chart_report["country_chart_dir"]).glob("*.png"):
        shutil.copy2(chart_path, country_asset_dir / chart_path.name)
    return {
        "asset_dir": str(asset_dir),
        "combined_chart": str(combined_asset),
        "country_chart_dir": str(country_asset_dir),
    }


def run(
    run_id: str = DEFAULT_RUN_ID,
    source_dataset: Path | None = None,
    translated_dataset: Path | None = None,
    cache_path: Path | None = None,
    output_dir: Path | None = None,
    top_n: int = 20,
    api_key: str | None = None,
) -> dict[str, Any]:
    run_dir = INTERMEDIATE_DATA_DIR / "pipeline_runs" / run_id
    datasets_dir = run_dir / "datasets"
    source_dataset = source_dataset or datasets_dir / "dataset_original_pages.jsonl"
    translated_dataset = translated_dataset or datasets_dir / "dataset_english_pages_tfidf.jsonl"
    cache_path = cache_path or datasets_dir / "translation_cache.json"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = output_dir or LEXICAL_ANALYSIS_DIR / f"tfidf_all_countries_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = output_dir / "tfidf_run_manifest.json"
    partial_path = translated_dataset.with_suffix(translated_dataset.suffix + ".tmp")
    manifest: dict[str, Any] = {
        "status": "translation_running",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "source_dataset": str(source_dataset),
        "translated_dataset": str(translated_dataset),
        "translation_cache": str(cache_path),
        "translation_model": TRANSLATION_MODEL,
        "output_dir": str(output_dir),
        "translation_resume_policy": "Rebuild output from source pages and reuse successful entries from translation_cache.json.",
        "footer_header_removal": False,
        "source_text_preserved": True,
    }
    _write_manifest(manifest_path, manifest)

    try:
        if not source_dataset.is_file():
            raise FileNotFoundError(f"Dataset original não encontrado: {source_dataset}")
        if translated_dataset.resolve() == source_dataset.resolve():
            raise ValueError("O dataset traduzido não pode sobrescrever o dataset original.")
        load_dotenv(Path(__file__).resolve().parent / ".env")
        resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY", "").strip()
        if not resolved_api_key:
            raise RuntimeError("Configure OPENAI_API_KEY em rag_project/.env ou no ambiente.")

        translation_report = build_english_page_dataset(
            source_dataset,
            translated_dataset,
            resolved_api_key,
            cache_path,
        )
        coverage = verify_translation_coverage(source_dataset, translated_dataset)
        manifest.update({
            "status": "translation_complete",
            "source_sha256": _sha256(source_dataset),
            "translated_sha256": _sha256(translated_dataset),
            "translation_cache_sha256": _sha256(cache_path),
            "translation_report": translation_report,
            "translation_coverage": coverage,
        })
        _write_manifest(manifest_path, manifest)

        analysis_dir = output_dir / "analysis"
        analysis_summary = analyze_within_country(
            str(translated_dataset),
            str(analysis_dir),
            text_field="english_text",
            top_n=top_n,
        )
        if analysis_summary["profiles"] != len(coverage["countries"]):
            raise ValueError(
                "A análise não gerou um perfil para cada país da origem: "
                f"perfis={analysis_summary['profiles']}, países={len(coverage['countries'])}."
            )
        chart_report = generate_tfidf_charts(analysis_dir)
        asset_report = export_tfidf_chart_assets(chart_report, output_dir)
        chart_report["versioned_assets"] = asset_report
        manifest.update({
            "status": "completed",
            "analysis_summary": analysis_summary,
            "analysis_dir": str(analysis_dir),
            "charts": chart_report,
            "tfidf_parameters": {
                "unit": "document aggregated within each country",
                "ngram_range": [1, 2],
                "min_df": 1,
                "max_df": 1.0,
                "max_features": 10000,
                "token_pattern": r"(?u)\b\w{3,}\b",
                "stop_words": sorted(STOP_WORDS),
                "cross_country_scores": False,
                "header_footer_cleaning": False,
            },
            "outputs": [
                str(analysis_dir / "country_profiles.csv"),
                str(analysis_dir / "country_local_top_terms.csv"),
                str(analysis_dir / "country_local_frequency.csv"),
                str(analysis_dir / "analysis_summary.json"),
                chart_report["combined_chart"],
                chart_report["country_chart_dir"],
                asset_report["combined_chart"],
                asset_report["country_chart_dir"],
            ],
        })
        _write_manifest(manifest_path, manifest)
        return manifest
    except BaseException as exc:
        manifest.update({
            "status": "failed",
            "error_type": type(exc).__name__,
            "partial_translation": _partial_dataset_status(partial_path),
            "translation_cache_sha256": _sha256(cache_path) if cache_path.is_file() else None,
        })
        _write_manifest(manifest_path, manifest)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Traduz páginas via API/cache e gera TF-IDF intrapaís para todos os países da origem."
    )
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--source", type=Path, default=None, help="Dataset original de páginas da rodada")
    parser.add_argument("--translated", type=Path, default=None, help="Destino do dataset traduzido")
    parser.add_argument("--cache", type=Path, default=None, help="Cache de traduções reutilizáveis")
    parser.add_argument("--out", type=Path, default=None, help="Diretório novo para esta execução")
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()
    result = run(
        run_id=args.run_id,
        source_dataset=args.source,
        translated_dataset=args.translated,
        cache_path=args.cache,
        output_dir=args.out,
        top_n=args.top_n,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()