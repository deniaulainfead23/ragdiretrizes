from __future__ import annotations

import argparse
import csv
from pathlib import Path

from rag_project.corpus_registry import EXCLUDED_COUNTRIES, ELIGIBLE_EXTENSIONS, _is_eligible_file, load_registry


BENCHMARK_DIRECTORIES = {"pisa", "unesco"}


def build_reconciliation(corpus_root: Path, registry_path: Path) -> list[dict[str, str]]:
    registry = load_registry(registry_path)
    declared: dict[tuple[str, str], dict] = {}
    countries = {entry["country"]: entry for entry in registry.get("countries", [])}
    for entry in registry.get("countries", []):
        for document in entry.get("documents", []) or []:
            declared[(entry["country"], document["file"])] = document

    rows: list[dict[str, str]] = []
    for country_dir in sorted(path for path in corpus_root.iterdir() if path.is_dir()):
        country = country_dir.name
        if country.lower() in EXCLUDED_COUNTRIES or country.lower() in BENCHMARK_DIRECTORIES:
            continue
        entry = countries.get(country, {})
        for path in sorted(path for path in country_dir.rglob("*") if _is_eligible_file(path)):
            relative_file = path.relative_to(country_dir).as_posix()
            document = declared.get((country, relative_file))
            if document:
                decision = document.get("validation_status", "pending_review")
                reason = "declared_in_registry"
                document_id = document.get("document_id", "")
                role = document.get("role", "")
            else:
                decision = "review_required"
                reason = "physical_file_not_declared_in_registry"
                document_id = ""
                role = ""
            rows.append({
                "country": country,
                "country_code": entry.get("country_code", ""),
                "file": relative_file,
                "document_id": document_id,
                "role": role,
                "registry_status": decision,
                "reconciliation_decision": decision,
                "reason": reason,
                "eligible_extension": "yes" if path.suffix.lower() in ELIGIBLE_EXTENSIONS else "no",
                "source_path": path.as_posix(),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita arquivos físicos contra o registry do corpus.")
    parser.add_argument("--corpus", default="corpus")
    parser.add_argument("--registry", default="rag_project/config/corpus_registry.yaml")
    parser.add_argument("--out", default="analysis/consolidado/reconciliacao_corpus.csv")
    args = parser.parse_args()

    rows = build_reconciliation(Path(args.corpus), Path(args.registry))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["country", "file"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)}")
    print(f"output={output}")


if __name__ == "__main__":
    main()