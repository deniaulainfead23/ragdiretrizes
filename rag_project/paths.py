"""Caminhos canônicos das camadas de dados do projeto."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = ROOT / "dados_brutos"
INTERMEDIATE_DATA_DIR = ROOT / "dados_intermediarios"
DERIVED_DATA_DIR = ROOT / "dados_derivados"

CORPUS_DIR = RAW_DATA_DIR / "corpus"
METADATA_DIR = INTERMEDIATE_DATA_DIR / "metadata"
PROCESSED_DIR = INTERMEDIATE_DATA_DIR / "processed"
PROCESSED_OCR_DIR = INTERMEDIATE_DATA_DIR / "processed_ocr"
DATASET_DIR = INTERMEDIATE_DATA_DIR / "datasets"
LEXICAL_ANALYSIS_DIR = INTERMEDIATE_DATA_DIR / "analise_lexical"
ANALYSIS_DIR = DERIVED_DATA_DIR / "analysis"