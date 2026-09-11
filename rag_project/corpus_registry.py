from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


EXCLUDED_COUNTRIES = {"marrocos"}
REGISTRY_PATH = Path(__file__).resolve().parent / "config" / "corpus_registry.yaml"
CORPUS_PATH = REGISTRY_PATH.parents[2] / "corpus"
ELIGIBLE_EXTENSIONS = {".pdf", ".html", ".htm", ".txt"}
INVALID_FILE_TOKENS = {
    "falha",
    "indisponivel",
    "downloads_log",
    "readme",
    "segunda_tentativa",
}


def load_registry(path: str | Path = REGISTRY_PATH) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def get_country(registry: dict, country: str) -> dict | None:
    country_key = country.strip().lower()
    return next((item for item in registry.get("countries", []) if item.get("country") == country_key), None)


def _is_eligible_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in ELIGIBLE_EXTENSIONS
        and not any(token in path.name.lower() for token in INVALID_FILE_TOKENS)
    )


def _discovered_documents(entry: dict) -> list[dict]:
    country_dir = CORPUS_PATH / entry["country"]
    if not country_dir.exists():
        return []

    prefix = hashlib.sha256(entry["country"].encode("utf-8")).hexdigest()[:8].upper()
    documents = []
    for number, path in enumerate(sorted(candidate for candidate in country_dir.rglob("*") if _is_eligible_file(candidate)), start=1):
        documents.append({
            "document_id": f"DISC-{prefix}-{number:02d}",
            "file": path.relative_to(country_dir).as_posix(),
            "role": "primary" if number == 1 else "complementary",
            "validation_status": "pending_review",
            "discovered_from_corpus": True,
        })
    return documents


def registered_documents(registry: dict, country: str | None = None):
    countries = registry.get("countries", [])
    if country is not None:
        countries = [get_country(registry, country)]
    for entry in countries:
        if not entry or entry.get("country") in EXCLUDED_COUNTRIES or not entry.get("include_in_analysis"):
            continue
        documents = entry.get("documents", []) or []
        for document in documents:
            if document.get("validation_status") != "validated":
                continue
            if document.get("role") not in {"primary", "complementary"}:
                continue
            yield entry, document


def registry_document_map(registry: dict, country: str | None = None) -> dict[tuple[str, str], dict]:
    return {(entry["country"], document["file"]): document for entry, document in registered_documents(registry, country)}