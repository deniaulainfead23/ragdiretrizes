from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from rag_project.corpus_registry import EXCLUDED_COUNTRIES, load_registry, registered_documents
from rag_project.paths import CORPUS_DIR, INTERMEDIATE_DATA_DIR


PIPELINE_VERSION = "1.0.0"
ELIGIBLE_EXTENSIONS = {".pdf", ".html", ".htm", ".txt"}
INVALID_FILE_TOKENS = ("falha", "indisponivel", "downloads_log", "readme", "segunda_tentativa")
REGISTRY_PATH = Path(__file__).resolve().parent / "config" / "corpus_registry.yaml"
QUESTIONS_PATH = Path(__file__).resolve().parent / "questions" / "questions.yaml"
DLGF_FRAMEWORK_PATH = Path(__file__).resolve().parent / "framework" / "unesco_dlgf_2018.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def eligible_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in ELIGIBLE_EXTENSIONS
        and not any(token in path.name.lower() for token in INVALID_FILE_TOKENS)
    )


def audit_corpus(corpus_root: Path, registry: dict) -> dict:
    curated = {}
    country_folders = set()
    for entry in registry.get("countries", []):
        if entry.get("country") in EXCLUDED_COUNTRIES or not entry.get("include_in_analysis"):
            continue
        country = entry["country"].lower()
        country_folders.add(country)
        for document in entry.get("documents", []) or []:
            if document.get("role") in {"primary", "complementary"}:
                curated[(country, document["file"])] = document
    verified = {
        (entry["country"].lower(), document["file"]): document
        for entry, document in registered_documents(registry)
    }

    actual_files = sorted(path for path in corpus_root.rglob("*") if eligible_file(path))
    actual = {}
    for path in actual_files:
        relative_path = path.relative_to(corpus_root)
        if len(relative_path.parts) >= 2 and relative_path.parts[0].lower() in country_folders:
            actual[(relative_path.parts[0].lower(), Path(*relative_path.parts[1:]).as_posix())] = path

    missing_verified = sorted(f"{country}/{filename}" for country, filename in verified if (country, filename) not in actual)
    unregistered = sorted(f"{country}/{filename}" for country, filename in actual if (country, filename) not in curated)
    pending_validation = sorted(
        f"{country}/{filename}"
        for (country, filename), document in curated.items()
        if (country, filename) in actual and document.get("validation_status") != "validated"
    )
    inventory = [
        {
            "country": country,
            "path": filename,
            "document_id": curated.get((country, filename), {}).get("document_id", ""),
            "document_role": curated.get((country, filename), {}).get("role", ""),
            "registry_validation_status": curated.get((country, filename), {}).get("validation_status", "unregistered"),
            "inclusion_decision": "included_verified" if (country, filename) in verified else "excluded_not_previously_verified",
            "sha256": sha256_file(actual[(country, filename)]),
        }
        for country, filename in sorted(actual)
    ]
    verified_present = [key for key in verified if key in actual]
    return {
        "corpus_root": str(corpus_root),
        "curated_documents": len(curated),
        "verified_selected_documents": len(verified),
        "verified_present_documents": len(verified_present),
        "discovered_documents": len(actual),
        "missing_verified_files": missing_verified,
        "unregistered_excluded_files": unregistered,
        "pending_verification_excluded_files": pending_validation,
        "inventory": inventory,
        # Pending and undiscovered documents are recorded and excluded. They do
        # not invalidate a build of the already validated subset. A missing
        # validated source remains a hard error because it breaks traceability.
        "is_buildable": bool(verified_present) and not missing_verified,
    }


def write_manifest(path: Path, manifest: dict) -> None:
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(path)


def build_page_dataset(corpus_root: Path, output_path: Path, registry: dict) -> dict:
    """Extract only registry-validated documents into a run-local page JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_rows = []
    record_count = 0
    included_documents = 0
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
        for entry, document in registered_documents(registry):
            source = corpus_root / entry["country"] / document["file"]
            if source.suffix.lower() == ".pdf":
                from rag_project.rag.ingest import extract_pdf_pages

                pages = extract_pdf_pages(str(source))
            else:
                try:
                    extracted = source.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    extracted = source.read_text(encoding="latin-1")
                pages = [(1, extracted)] if extracted.strip() else []

            written = 0
            for page_number, page_text in pages:
                page_text = str(page_text).strip()
                if not page_text:
                    continue
                content_id = f"{document['document_id']}_p{int(page_number):04d}"
                record = {
                    "content_id": content_id,
                    "chunk_id": content_id,
                    "document_id": document["document_id"],
                    "country": entry["country"],
                    "country_code": entry.get("country_code", ""),
                    "source_scope": "national",
                    "framework_source": "",
                    "document_title": Path(document["file"]).stem,
                    "year": "",
                    "language": document.get("language", ""),
                    "page_start": page_number,
                    "page_end": page_number,
                    "source_text": page_text,
                    "char_count": len(page_text),
                    "token_estimate": max(1, round(len(page_text) / 4)),
                    "document_role": document["role"],
                    "validation_status": document["validation_status"],
                    "source_path": source.relative_to(corpus_root.parent).as_posix(),
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                record_count += 1
                written += 1
            status = "included" if written else "no_extractable_text"
            if written:
                included_documents += 1
            report_rows.append({
                "document_id": document["document_id"],
                "source_path": source.relative_to(corpus_root.parent).as_posix(),
                "processing_status": status,
                "pages_written": str(written),
                "validation_status": document["validation_status"],
            })
    if record_count == 0:
        temporary_path.unlink(missing_ok=True)
        raise ValueError("Nenhuma página com texto foi extraída dos documentos validados.")
    temporary_path.replace(output_path)
    report_path = output_path.with_name("dataset_build_report.csv")
    import csv
    with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["document_id", "source_path", "processing_status", "pages_written", "validation_status"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report_rows)
    return {
        "documents_included": included_documents,
        "pages_written": record_count,
        "report_path": str(report_path),
    }


def run(corpus_root: Path, output_root: Path, run_id: str, build_outputs: bool) -> int:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", run_id):
        raise ValueError("run-id aceita apenas letras, números, ponto, hífen e underscore")

    corpus_root = corpus_root.resolve()
    output_root = output_root.resolve()
    if not corpus_root.is_dir():
        raise FileNotFoundError(f"Pasta do corpus não encontrada: {corpus_root}")
    if output_root == corpus_root or corpus_root in output_root.parents:
        raise ValueError("A pasta de saída não pode ficar dentro do corpus")

    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    registry = load_registry()
    audit = audit_corpus(corpus_root, registry)
    manifest = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": run_id,
        "identifier": f"local:{run_id}",
        "title": "RAG comparativo de currículos de Computação na Educação Básica",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "preflight_blocked" if not audit["is_buildable"] else "preflight_passed",
        "corpus_version": str(registry.get("corpus_version", "")),
        "registry_sha256": sha256_file(REGISTRY_PATH),
        "questions_sha256": sha256_file(QUESTIONS_PATH),
        "dlgf_framework_sha256": sha256_file(DLGF_FRAMEWORK_PATH),
        "build_requested": build_outputs,
        "fair_metadata": {
            "findable": {"local_identifier": f"local:{run_id}", "metadata_standard": "project-run-manifest-v1"},
            "accessible": {"storage": "workspace-local", "formats": ["CSV", "JSONL", "JSON", "FAISS"]},
            "interoperable": {"text_encoding": "UTF-8", "tabular_formats": ["CSV", "JSONL"]},
            "reusable": {"provenance_recorded": True, "source_rights": "See per-document official source and license; not reassigned by this run."},
        },
        "software": {"python": sys.version.split()[0]},
        "audit": audit,
        "outputs": {},
        "errors": [],
    }
    manifest_path = run_dir / "run_manifest.json"
    write_manifest(manifest_path, manifest)

    print(f"Rodada: {run_id}")
    print(f"Corpus encontrado: {audit['discovered_documents']}")
    print(f"Documentos curados no registro: {audit['curated_documents']}")
    print(f"Documentos previamente verificados presentes: {audit['verified_present_documents']}")
    print(f"Arquivos verificados ausentes: {len(audit['missing_verified_files'])}")
    print(f"Arquivos pendentes/não verificados excluídos: {len(audit['pending_verification_excluded_files'])}")
    print(f"Arquivos não registrados excluídos: {len(audit['unregistered_excluded_files'])}")
    print(f"Manifesto: {manifest_path}")

    if not audit["is_buildable"]:
        error_type = "MissingValidatedSources" if audit["missing_verified_files"] else "NoValidatedDocuments"
        manifest["errors"].append({"stage": "preflight", "error_type": error_type, "message": "Preflight requer ao menos um documento validado presente e nenhum documento validado ausente."})
        write_manifest(manifest_path, manifest)
        print("Construção interrompida: preflight encontrou divergências ou nenhum documento verificado presente.")
        return 2
    if not build_outputs:
        print("Pré-verificação concluída. Nenhum dataset ou índice foi construído.")
        return 0

    dataset_dir = run_dir / "datasets"
    index_dir = run_dir / "index"
    content_dataset_path = dataset_dir / "dataset_pages.jsonl"
    manifest["status"] = "building"
    write_manifest(manifest_path, manifest)
    try:
        from rag_project.build_index import build_from_dataset

        dataset_report = build_page_dataset(corpus_root, content_dataset_path, registry)
        index_report = build_from_dataset(str(content_dataset_path), str(index_dir))
        manifest["outputs"] = {
            "dataset_pages": {
                "path": str(content_dataset_path),
                "sha256": sha256_file(content_dataset_path),
            },
            "dataset_build_report": {
                "path": dataset_report["report_path"],
                "sha256": sha256_file(Path(dataset_report["report_path"])),
                "summary": dataset_report,
            },
            "index": {
                "path": str(index_dir),
                "index_sha256": sha256_file(index_dir / "index.faiss"),
                "metadata_sha256": sha256_file(index_dir / "metadatas.json"),
                "build_report": index_report,
            },
        }
        manifest["status"] = "built"
    except Exception as exc:
        manifest["status"] = "build_failed"
        manifest["errors"].append({"stage": "dataset_or_index", "error_type": type(exc).__name__})
        write_manifest(manifest_path, manifest)
        raise

    write_manifest(manifest_path, manifest)
    print(f"Dataset e índice novos salvos em: {run_dir}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audita o corpus curado e, mediante --build, cria dataset e índice em uma rodada nova."
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS_DIR, help="Pasta do corpus curado")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=INTERMEDIATE_DATA_DIR / "pipeline_runs",
        help="Raiz para as saídas isoladas das rodadas",
    )
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("curated_%Y%m%dT%H%M%SZ"),
        help="Identificador único da rodada; uma pasta existente nunca é sobrescrita",
    )
    parser.add_argument("--build", action="store_true", help="Após auditoria aprovada, gerar datasets e índice local")
    args = parser.parse_args()
    raise SystemExit(run(args.corpus, args.output_root, args.run_id, args.build))


if __name__ == "__main__":
    main()
