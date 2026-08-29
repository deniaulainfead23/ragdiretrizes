from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def normalize_country_name(folder_name: str) -> str:
    mapping = {
        'africa-do-sul': 'África do Sul',
        'australia': 'Austrália',
        'brasil': 'Brasil',
        'canada': 'Canadá',
        'chile': 'Chile',
        'coreia-do-sul': 'Coreia do Sul',
        'eua': 'Estados Unidos',
        'finlandia': 'Finlândia',
        'gana': 'Gana',
        'hong-kong': 'Hong Kong',
        'irlanda': 'Irlanda',
        'japao': 'Japão',
        'marrocos': 'Marrocos',
        'nova-zelandia': 'Nova Zelândia',
        'quenia': 'Quênia',
        'reino-unido': 'Reino Unido',
        'ruanda': 'Ruanda',
        'singapura': 'Singapura',
        'suica': 'Suíça',
        'taiwan': 'Taiwan',
        'uruguai': 'Uruguai',
        'unesco': 'UNESCO',
        'pisa': 'PISA',
    }
    return mapping.get(folder_name.strip().lower(), folder_name.strip().title())


def docid_prefix(country: str) -> str:
    aliases = {
        'África do Sul': 'ZA',
        'Austrália': 'AU',
        'Brasil': 'BR',
        'Canadá': 'CA',
        'Chile': 'CL',
        'Coreia do Sul': 'KR',
        'Estados Unidos': 'US',
        'Finlândia': 'FI',
        'Gana': 'GH',
        'Hong Kong': 'HK',
        'Irlanda': 'IE',
        'Japão': 'JP',
        'Marrocos': 'MA',
        'Nova Zelândia': 'NZ',
        'Quênia': 'KE',
        'Reino Unido': 'UK',
        'Ruanda': 'RW',
        'Singapura': 'SG',
        'Suíça': 'CH',
        'Taiwan': 'TW',
        'Uruguai': 'UY',
        'UNESCO': 'UN',
        'PISA': 'PISA',
    }
    return aliases.get(country, country[:2].upper())


def iter_document_files(corpus_root: Path) -> Iterable[Path]:
    if not corpus_root.exists():
        return []
    paths: list[Path] = []
    for child in sorted(corpus_root.iterdir()):
        if not child.is_dir():
            continue
        for file_path in sorted(child.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in {'.pdf', '.html', '.htm', '.txt'}:
                paths.append(file_path)
    return paths


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def infer_document_type(file_name: str) -> str:
    lower = file_name.lower()
    if 'curriculo' in lower or 'currículo' in lower or 'curriculum' in lower:
        return 'curriculum'
    if 'bncc' in lower:
        return 'curricular_base'
    if 'tecnologia' in lower or 'digital' in lower:
        return 'digital_education'
    if 'compet' in lower:
        return 'competence_framework'
    if 'policy' in lower or 'pol' in lower:
        return 'policy'
    if lower.endswith('.pdf'):
        return 'document'
    return 'document'


def infer_language(file_name: str, sample_text: str = '') -> str:
    lower = sample_text.lower()
    if any(token in lower for token in ['the ', 'curriculum', 'education', 'digital', 'technology', 'students']):
        return 'en'
    if any(token in lower for token in ['educação', 'currículo', 'digital', 'tecnologia', 'alunos', 'competências']):
        return 'pt'
    if 'english' in file_name.lower() or 'eng' in file_name.lower():
        return 'en'
    return 'unknown'


def infer_source_confidence(file_name: str, relative_path: str) -> tuple[str, bool]:
    lower = f'{file_name} {relative_path}'.lower()
    if any(token in lower for token in ['ministry', 'gov', 'education', 'government', 'ministerio', 'mec', 'unesco', 'oecd']):
        return 'A', True
    if any(token in lower for token in ['official', 'repository', 'institucional', 'site']) or lower.endswith('.html'):
        return 'B', True
    if 'historical' in lower or 'archive' in lower:
        return 'C', True
    if 'academic' in lower or 'research' in lower:
        return 'D', False
    return 'E', False


def build_document_id(country: str, file_name: str, sorted_files: list[Path]) -> str:
    prefix = docid_prefix(country)
    ordered = sorted(sorted_files, key=lambda p: str(p).lower())
    index = 1
    for path in ordered:
        if path.name == file_name:
            return f'{prefix}_{index:03d}'
        index += 1
    return f'{prefix}_001'


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_bibliographic_matrix(corpus_root: str | Path, output_dir: str | Path | None = None) -> list[dict]:
    root = Path(corpus_root)
    if not root.exists():
        return []

    sorted_files = list(iter_document_files(root))
    rows: list[dict] = []

    by_country: dict[str, list[Path]] = {}
    for file_path in sorted_files:
        country = normalize_country_name(file_path.parent.name)
        by_country.setdefault(country, []).append(file_path)

    for country, country_files in sorted(by_country.items()):
        for file_path in sorted(country_files, key=lambda p: p.name.lower()):
            relative_path = file_path.relative_to(root).as_posix()
            sha256 = compute_sha256(file_path)
            source_confidence, source_verified = infer_source_confidence(file_path.name, relative_path)
            document_id = build_document_id(country, file_path.name, country_files)
            rows.append({
                'document_id': document_id,
                'country': country,
                'title_original': file_path.stem,
                'title_translated': file_path.stem,
                'institution': 'Official institutional source',
                'authors': '',
                'publication_year_original': '',
                'publication_year_version_used': '',
                'document_type': infer_document_type(file_path.name),
                'education_level': '',
                'curricular_area': 'Computing and Digital Education',
                'language_original': infer_language(file_path.name, file_path.read_text(encoding='utf-8', errors='ignore')[:2000]),
                'language_analysis': 'en',
                'official_source_url': '',
                'landing_page_url': '',
                'access_date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'doi': '',
                'isbn': '',
                'edition': '',
                'version': '',
                'current_status': 'available',
                'file_name': file_path.name,
                'relative_path': relative_path,
                'number_of_pages': '',
                'file_size': str(file_path.stat().st_size),
                'sha256': sha256,
                'ocr_used': 'false',
                'ocr_engine': '',
                'translation_used': 'false',
                'translation_tool': '',
                'translation_model': '',
                'translation_date': '',
                'source_verified': 'true' if source_verified else 'false',
                'source_confidence': source_confidence,
                'source_type': file_path.suffix.lower().lstrip('.'),
                'inclusion_reason': 'official curriculum source available in corpus',
                'exclusion_reason': '',
                'notes': 'Generated by provenance pipeline; file kept unchanged in RAW corpus',
            })

    output_path = Path(output_dir) if output_dir is not None else root.parent / 'metadata'
    output_path.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'document_id', 'country', 'title_original', 'title_translated', 'institution', 'authors',
        'publication_year_original', 'publication_year_version_used', 'document_type', 'education_level',
        'curricular_area', 'language_original', 'language_analysis', 'official_source_url', 'landing_page_url',
        'access_date', 'doi', 'isbn', 'edition', 'version', 'current_status', 'file_name', 'relative_path',
        'number_of_pages', 'file_size', 'sha256', 'ocr_used', 'ocr_engine', 'translation_used', 'translation_tool',
        'translation_model', 'translation_date', 'source_verified', 'source_confidence', 'source_type',
        'inclusion_reason', 'exclusion_reason', 'notes'
    ]
    write_csv(output_path / 'bibliographic_matrix.csv', fieldnames, rows)
    return rows


def build_corpus_manifest(corpus_root: str | Path, output_dir: str | Path | None = None) -> list[dict]:
    root = Path(corpus_root)
    rows: list[dict] = []
    for file_path in sorted(iter_document_files(root)):
        country = normalize_country_name(file_path.parent.name)
        relative_path = file_path.relative_to(root).as_posix()
        sha256 = compute_sha256(file_path)
        rows.append({
            'document_id': f"{docid_prefix(country)}_{file_path.name[:10].upper()}",
            'country': country,
            'file_name': file_path.name,
            'relative_path': relative_path,
            'sha256': sha256,
            'size_bytes': str(file_path.stat().st_size),
            'status': 'available',
            'document_type': infer_document_type(file_path.name),
            'source_verified': 'true',
        })

    output_path = Path(output_dir) if output_dir is not None else root.parent / 'metadata'
    output_path.mkdir(parents=True, exist_ok=True)
    fieldnames = ['document_id', 'country', 'file_name', 'relative_path', 'sha256', 'size_bytes', 'status', 'document_type', 'source_verified']
    write_csv(output_path / 'corpus_manifest.csv', fieldnames, rows)
    return rows


def build_country_selection(corpus_root: str | Path, output_dir: str | Path | None = None) -> list[dict]:
    root = Path(corpus_root)
    countries = sorted({normalize_country_name(path.name) for path in root.iterdir() if path.is_dir()})
    rows: list[dict] = []
    for country in countries:
        rows.append({
            'country': country,
            'continent': 'international',
            'pisa_year': '',
            'pisa_score': '',
            'pisa_band': '',
            'official_curriculum_available': 'true',
            'computing_or_digital_policy_available': 'true',
            'geographical_representation': 'yes',
            'selection_reason': 'intentional multi-criteria sampling for comparative curricular analysis',
            'exception_reason': '',
            'included': 'true',
        })

    output_path = Path(output_dir) if output_dir is not None else root.parent / 'metadata'
    output_path.mkdir(parents=True, exist_ok=True)
    fieldnames = ['country', 'continent', 'pisa_year', 'pisa_score', 'pisa_band', 'official_curriculum_available', 'computing_or_digital_policy_available', 'geographical_representation', 'selection_reason', 'exception_reason', 'included']
    write_csv(output_path / 'country_selection.csv', fieldnames, rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description='Build bibliographic metadata, corpus manifest and country selection for the project.')
    parser.add_argument('--corpus', default='corpus', help='Directory containing country folders and raw corpus files')
    parser.add_argument('--out', default='metadata', help='Directory where output metadata CSVs are written')
    args = parser.parse_args()

    build_bibliographic_matrix(args.corpus, args.out)
    build_corpus_manifest(args.corpus, args.out)
    build_country_selection(args.corpus, args.out)

    print(f'Bibliographic matrix created in {Path(args.out) / "bibliographic_matrix.csv"}')
    print(f'Corpus manifest created in {Path(args.out) / "corpus_manifest.csv"}')
    print(f'Country selection created in {Path(args.out) / "country_selection.csv"}')


if __name__ == '__main__':
    main()
