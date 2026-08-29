from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterator, Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

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


def iter_valid_documents(corpus_root: Path) -> Iterator[tuple[str, Path]]:
    if not corpus_root.exists():
        return
    for child in sorted(corpus_root.iterdir()):
        if not child.is_dir():
            continue
        for file in sorted(child.iterdir()):
            if is_valid_file(file):
                yield child.name, file


def dataset_group_for_folder(folder_name: str) -> str:
    return 'unesco' if folder_name.strip().lower() == 'unesco' else 'country'


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
    }


def translate_to_english(client: OpenAI, text: str, max_chars: int = 7000) -> str:
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


def write_dataset_stream(corpus_root: Path, output_path: Path, use_openai_translation: bool = False, openai_api_key: Optional[str] = None, dataset_group: str = 'country'):
    client = None
    if use_openai_translation and openai_api_key:
        if OpenAI is None:
            raise RuntimeError('openai package not installed')
        client = OpenAI(api_key=openai_api_key)

    count = 0
    with output_path.open('w', encoding='utf-8') as handle:
        for country, source_path in iter_valid_documents(corpus_root):
            source_text = extract_text_from_file(source_path)
            if not source_text.strip():
                continue
            translated_text = source_text
            if use_openai_translation and client is not None:
                try:
                    translated_text = translate_to_english(client, source_text)
                except Exception as exc:  # pragma: no cover
                    print(f'Warning: translation failed for {source_path.name}: {exc}')
                    translated_text = source_text
            record_group = dataset_group_for_folder(country)
            record = make_dataset_record(country, source_path, corpus_root, source_text, translated_text, record_group)
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')
            count += 1
            print(f'[{record_group}] {count}: {country} / {source_path.name}')
    print(f'Dataset saved: {output_path} ({count} records)')


def build_bilingual_datasets(corpus_root: str, output_dir: str, openai_api_key: Optional[str] = None, use_openai_translation: bool = False):
    root = Path(corpus_root)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    original_path = out_dir / 'dataset_original.jsonl'
    english_path = out_dir / 'dataset_english.jsonl'

    # 1) original dataset: keep source text untouched
    write_dataset_stream(root, original_path, use_openai_translation=False, openai_api_key=None, dataset_group='country')

    # 2) english dataset: same documents but translated for analysis
    if use_openai_translation and openai_api_key:
        write_dataset_stream(root, english_path, use_openai_translation=True, openai_api_key=openai_api_key, dataset_group='country')
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

    build_bilingual_datasets(
        corpus_root=args.corpus,
        output_dir=args.out,
        openai_api_key=args.openai_key,
        use_openai_translation=args.translate,
    )
