from __future__ import annotations

from pathlib import Path

import yaml


EXCLUDED_COUNTRIES = {"marrocos"}
REGISTRY_PATH = Path(__file__).resolve().parent / "config" / "corpus_registry.yaml"


def load_registry(path: str | Path = REGISTRY_PATH) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def get_country(registry: dict, country: str) -> dict | None:
    country_key = country.strip().lower()
    return next((item for item in registry.get("countries", []) if item.get("country") == country_key), None)


def registered_documents(registry: dict, country: str | None = None):
    countries = registry.get("countries", [])
    if country is not None:
        countries = [get_country(registry, country)]
    for entry in countries:
        if not entry or entry.get("country") in EXCLUDED_COUNTRIES or not entry.get("include_in_analysis"):
            continue
        for document in entry.get("documents", []):
            if document.get("validation_status") == "rejected":
                continue
            if document.get("role") not in {"primary", "complementary"}:
                continue
            yield entry, document


def registry_document_map(registry: dict, country: str | None = None) -> dict[tuple[str, str], dict]:
    return {(entry["country"], document["file"]): document for entry, document in registered_documents(registry, country)}