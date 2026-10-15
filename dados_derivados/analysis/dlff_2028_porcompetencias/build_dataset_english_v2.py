#!/usr/bin/env python3
"""Build a traceable English corpus while preserving the original page text."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


MODEL = "gpt-4o-mini"
TEMPERATURE = 0.0
MAX_TOKENS = 2200
CHUNK_CHARS = 6000
ENGLISH_TERMS = {
    "and", "are", "as", "by", "for", "from", "in", "is", "of", "on",
    "or", "the", "their", "these", "this", "to", "with", "education",
    "curriculum", "students", "digital", "learning", "school",
}
WORD_RE = re.compile(r"(?u)\b[\w'-]+\b")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def likely_english(text: str) -> bool:
    if not text.strip() or re.search(r"[\u1100-\u11ff\u3040-\u30ff\u3130-\u318f\u3400-\u9fff\uac00-\ud7a3]", text):
        return False
    words = [word.casefold() for word in WORD_RE.findall(text)]
    if not words:
        return False
    hits = sum(word in ENGLISH_TERMS for word in words)
    accented = sum(any(ord(char) > 127 for char in word) for word in words)
    minimum_hits = 1 if len(words) <= 20 else 2
    return hits >= minimum_hits and hits / len(words) >= 0.04 and accented / len(words) < 0.08


def split_text(text: str) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()
    while len(remaining) > CHUNK_CHARS:
        cut = remaining.rfind(" ", 0, CHUNK_CHARS)
        if cut < CHUNK_CHARS // 2:
            cut = CHUNK_CHARS
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def translate(client: OpenAI, text: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Translate educational policy and curriculum text into accurate English. "
                    "Do not summarize, omit, explain, or add content. Preserve numbering, "
                    "technical terms, names, and paragraph structure as much as possible."
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    translated = (response.choices[0].message.content or "").strip()
    if not translated:
        raise ValueError("A API retornou uma tradução vazia.")
    return translated


def translate_worker(api_key: str, text: str) -> str:
    return translate(OpenAI(api_key=api_key), text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.out).resolve()
    cache_path = Path(args.cache).resolve()
    report_path = Path(args.report).resolve()
    manifest_path = Path(args.manifest).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Dataset de origem não encontrado: {input_path}")

    load_dotenv(Path(__file__).resolve().parents[3] / "rag_project" / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada.")
    if args.workers < 1 or args.workers > 8:
        raise ValueError("--workers deve estar entre 1 e 8.")
    if args.batch_size < 1:
        raise ValueError("--batch-size deve ser positivo.")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[str, str] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    report_rows: list[dict[str, Any]] = []
    input_records = translated_records = retained_english = 0
    temporary_output = output_path.with_suffix(".tmp")
    with input_path.open("r", encoding="utf-8-sig") as source, temporary_output.open("w", encoding="utf-8") as target:
        batch: list[tuple[int, dict[str, Any]]] = []

        def write_batch(rows: list[tuple[int, dict[str, Any]]]) -> None:
            nonlocal input_records, translated_records, retained_english
            pending: dict[str, tuple[int, str, str]] = {}
            tasks = {}
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                for line_number, row in rows:
                    original = str(row.get("source_text") or "").strip()
                    if not original:
                        raise ValueError(f"Texto vazio na linha {line_number}.")
                    english_flag = likely_english(original)
                    segments = [original] if english_flag else split_text(original)
                    for segment_number, segment in enumerate(segments, start=1):
                        cache_key = hashlib.sha256(f"{MODEL}|{TEMPERATURE}|{segment}".encode("utf-8")).hexdigest()
                        if english_flag:
                            pending[cache_key] = (segment_number, segment, segment)
                        elif cache_key in cache:
                            pending[cache_key] = (segment_number, segment, cache[cache_key])
                        else:
                            tasks[executor.submit(translate_worker, api_key, segment)] = (
                                cache_key, segment_number, segment
                            )
                for future in as_completed(tasks):
                    cache_key, segment_number, segment = tasks[future]
                    try:
                        english = future.result()
                    except Exception as exc:
                        raise RuntimeError(
                            f"Falha na tradução em um bloco do lote iniciado na linha {rows[0][0]}"
                        ) from exc
                    cache[cache_key] = english
                    pending[cache_key] = (segment_number, segment, english)
            cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

            for line_number, row in rows:
                original = str(row["source_text"]).strip()
                english_flag = likely_english(original)
                segments = [original] if english_flag else split_text(original)
                status = "already_english" if english_flag else "translated"
                for segment_number, segment in enumerate(segments, start=1):
                    cache_key = hashlib.sha256(f"{MODEL}|{TEMPERATURE}|{segment}".encode("utf-8")).hexdigest()
                    _, _, english = pending[cache_key]
                    if status == "already_english":
                        retained_english += 1
                    else:
                        translated_records += 1
                    base_id = str(row.get("content_id") or row.get("chunk_id") or f"line_{line_number}")
                    output = dict(row)
                    output.update({
                        "content_id": f"{base_id}_en_v2_{segment_number:04d}",
                        "chunk_id": f"{base_id}_en_v2_{segment_number:04d}",
                        "page_source_content_id": base_id,
                        "source_text": segment,
                        "english_text": english,
                        "translation_status": status,
                        "translation_model": MODEL if status == "translated" else "",
                        "translation_temperature": TEMPERATURE if status == "translated" else "",
                        "translation_max_tokens": MAX_TOKENS if status == "translated" else "",
                        "translation_cache_key": hashlib.sha256(segment.encode("utf-8")).hexdigest(),
                    })
                    serialized = json.dumps(output, ensure_ascii=False).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
                    target.write(serialized + "\n")
                    report_rows.append({
                        "line_number": line_number,
                        "document_id": row.get("document_id", ""),
                        "country": row.get("country", ""),
                        "content_id": base_id,
                        "segment": segment_number,
                        "source_chars": len(segment),
                        "english_chars": len(english),
                        "translation_status": status,
                    })
                input_records += 1
            print(f"registros_processados={input_records}", flush=True)

        for line_number, line in enumerate(source, start=1):
            if line.strip():
                batch.append((line_number, json.loads(line)))
            if len(batch) >= args.batch_size:
                write_batch(batch)
                batch = []
        if batch:
            write_batch(batch)
    temporary_output.replace(output_path)

    with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(report_rows[0]) if report_rows else []
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report_rows)
    manifest = {
        "dataset_version": "english_v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(input_path), "sha256": sha256_file(input_path)},
        "output": {"path": str(output_path), "sha256": sha256_file(output_path)},
        "translation": {
            "provider": "OpenAI",
            "model": MODEL,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "chunk_chars": CHUNK_CHARS,
            "workers": args.workers,
            "batch_size": args.batch_size,
            "already_english_detection": "heuristic; CJK rejection, English function-word ratio, accent ratio",
            "cache_path": str(cache_path),
        },
        "counts": {
            "input_records": input_records,
            "output_records": len(report_rows),
            "translated_segments": translated_records,
            "retained_english_records": retained_english,
        },
        "provenance": "source_text is preserved per output segment; english_text is the analysis field.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
