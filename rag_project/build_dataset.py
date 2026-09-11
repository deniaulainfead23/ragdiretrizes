from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Iterator, Optional

from rag_project.corpus_registry import EXCLUDED_COUNTRIES, load_registry, registered_documents

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

INVALID_FILE_TOKENS = (
    'falha',
    'indisponivel',
    'downloads_log',
    'readme',
    'segunda_tentativa',
)
VALID_EXTENSIONS = {'.pdf', '.html', '.htm', '.txt'}


def is_valid_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() not in VALID_EXTENSIONS:
        return False
    name = path.name.lower()
    if any(token in name for token in INVALID_FILE_TOKENS):
        return False
    return True


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        try:
            try:
                from rag_project.rag.ingest import extract_pdf_pages
            except ImportError:
                from rag.ingest import extract_pdf_pages

            pages = extract_pdf_pages(str(path))
            return '\n\n'.join(page_text for _, page_text in pages)
        except Exception:
            return ''

    if suffix in {'.html', '.htm'}:
        text = path.read_text(encoding='utf-8', errors='ignore')
        text = re.sub(r'<script.*?</script>', ' ', text, flags=re.S | re.I)
        text = re.sub(r'<style.*?</style>', ' ', text, flags=re.S | re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    try:
        return path.read_text(encoding='utf-8', errors='ignore').strip()
    except Exception:
        try:
            return path.read_text(encoding='latin-1', errors='ignore').strip()
        except Exception:
            return ''


def iter_valid_documents(corpus_root: Path, registry: dict | None = None) -> Iterator[tuple[str, Path, dict, dict]]:
    if not corpus_root.exists():
        return
    registry = registry or load_registry()
    for country_entry, document in registered_documents(registry):
        if country_entry["country"] in EXCLUDED_COUNTRIES:
            continue
        file_path = corpus_root / country_entry["country"] / document["file"]
        if is_valid_file(file_path):
            yield country_entry["country"], file_path, country_entry, document


def dataset_group_for_folder(folder_name: str) -> str:
    normalized = folder_name.strip().lower()
    if normalized == 'unesco':
        return 'unesco'
    if normalized == 'pisa':
        return 'pisa'
    return 'country'


def detect_primary_language(text: str) -> str:
    sample = (text or '').lower()
    if any(ch in sample for ch in ('á', 'é', 'í', 'ó', 'ú', 'ã', 'õ', 'ç', 'ê', 'à', 'ô', 'ü', 'ñ')):
        return 'pt'
    if any(token in sample for token in ('the ', 'and ', 'education', 'curriculum', 'digital', 'learning')):
        return 'en'
    return 'unknown'


def make_dataset_record(country: str, source_path: Path, corpus_root: Path, source_text: str, translated_text: str, dataset_group: str) -> dict:
    rel_path = source_path.relative_to(corpus_root).as_posix()
    return {
        'country': country,
        'dataset_group': dataset_group,
        'document': source_path.name,
        'source_path': rel_path,
        'source_type': source_path.suffix.lower().lstrip('.'),
        'language_original': detect_primary_language(source_text),
        'language_analysis': 'en',
        'status': 'ready',
        'source_text': source_text,
        'english_text': translated_text,
        'year': '',
        'institution': '',
        'document_type': '',
        'theme': '',
        'unesco_reference': 'yes' if dataset_group == 'unesco' else 'no',
        'pisa_reference': 'yes' if dataset_group == 'pisa' else 'no',
    }


def translate_to_english(client: OpenAI, text: str, max_chars: int = 6000) -> str:
    if not text or not text.strip():
        return ''
    snippet = text[:max_chars]
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {
                'role': 'system',
                'content': 'You are translating educational policy text into clear and accurate English while preserving technical terms and meaning.',
            },
            {
                'role': 'user',
                'content': f'Translate this educational policy text to English. Preserve the original meaning and technical terms.\n\n{snippet}',
            },
        ],
        temperature=0.0,
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()


def translate_document_in_chunks(client: OpenAI, text: str, cache: dict, cache_path: Optional[Path] = None, chunk_chars: int = 6000) -> str:
    chunks = [text[start:start + chunk_chars] for start in range(0, len(text), chunk_chars)]
    translated_chunks = []
    for chunk_index, chunk in enumerate(chunks):
        cache_key = hashlib.sha256(f'v2:{chunk_index}:{chunk}'.encode('utf-8')).hexdigest()
        translated = cache.get(cache_key)
        if translated is None:
            translated = translate_to_english(client, chunk, max_chars=chunk_chars)
            cache[cache_key] = translated
            if cache_path:
                cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
        else:
            print(f'[translation-cache] bloco {chunk_index + 1}/{len(chunks)}')
        translated_chunks.append(translated)
    return '\n\n'.join(translated_chunks)


def write_dataset_stream(corpus_root: Path, output_path: Path, use_openai_translation: bool = False, openai_api_key: Optional[str] = None, dataset_group: str = 'country', translation_cache_path: Optional[Path] = None):
    client = None
    if use_openai_translation and openai_api_key:
        if OpenAI is None:
            raise RuntimeError('openai package not installed')
        client = OpenAI(api_key=openai_api_key)

    count = 0
    translation_cache = {}
    if translation_cache_path and translation_cache_path.exists():
        try:
            translation_cache = json.loads(translation_cache_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            translation_cache = {}
    with output_path.open('w', encoding='utf-8') as handle:
        for country, source_path, country_entry, document in iter_valid_documents(corpus_root):
            source_text = extract_text_from_file(source_path)
            if not source_text.strip():
                continue
            translated_text = source_text
            if use_openai_translation and client is not None:
                try:
                    translated_text = translate_document_in_chunks(client, source_text, translation_cache, translation_cache_path)
                except Exception as exc:  # pragma: no cover
                    print(f'Warning: translation failed for {source_path.name}: {exc}')
                    translated_text = source_text
            record_group = dataset_group_for_folder(country)
            record = make_dataset_record(country, source_path, corpus_root, source_text, translated_text, record_group)
            record.update({
                'country_code': country_entry['country_code'],
                'continent': country_entry['continent'],
                'document_id': document['document_id'],
                'document_role': document['role'],
                'validation_status': document['validation_status'],
                'corpus_version': '3.0',
            })
            # Escape Unicode line separators so each JSON object remains one JSONL line.
            handle.write(json.dumps(record, ensure_ascii=True) + '\n')
            count += 1
            print(f'[{record_group}] {count}: {country} / {source_path.name}')
    print(f'Dataset saved: {output_path} ({count} records)')


def build_bilingual_datasets(corpus_root: str, output_dir: str, openai_api_key: Optional[str] = None, use_openai_translation: bool = False):
    root = Path(corpus_root)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    original_path = out_dir / 'dataset_original.jsonl'
    english_path = out_dir / 'dataset_english.jsonl'
    translation_cache_path = out_dir / 'translation_cache.json'

    # 1) original dataset: keep source text untouched
    write_dataset_stream(root, original_path, use_openai_translation=False, openai_api_key=None, dataset_group='country')

    # 2) english dataset: same documents but translated for analysis
    if use_openai_translation and openai_api_key:
        write_dataset_stream(root, english_path, use_openai_translation=True, openai_api_key=openai_api_key, dataset_group='country', translation_cache_path=translation_cache_path)
    else:
        # if translation is not requested, english file remains a copy of original text to keep structure consistent
        write_dataset_stream(root, english_path, use_openai_translation=False, openai_api_key=None, dataset_group='country')

    print('\nBilingual dataset generation complete.')
    print(f'Original: {original_path}')
    print(f'English: {english_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gera dataset em idioma original e em inglês sem carregar todo o corpus na memória.')
    parser.add_argument('--corpus', default='corpus', help='Pasta do corpus principal')
    parser.add_argument('--out', default='corpus/dataset_output', help='Diretório para salvar os datasets')
    parser.add_argument('--openai_key', default=None, help='Chave OpenAI para tradução e upload de arquivos')
    parser.add_argument('--translate', action='store_true', help='Traduz os documentos para inglês via OpenAI')
    args = parser.parse_args()

    if not args.openai_key and load_dotenv is not None:
        load_dotenv(Path(__file__).resolve().parent / '.env')
        args.openai_key = os.environ.get('OPENAI_API_KEY')

    build_bilingual_datasets(
        corpus_root=args.corpus,
        output_dir=args.out,
        openai_api_key=args.openai_key,
        use_openai_translation=args.translate,
    )
