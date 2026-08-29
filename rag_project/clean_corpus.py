from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'corpus'

INVALID_PATTERNS = (
    'falha_download',
    'indisponivel',
    'downloads_log',
    'readme',
    'log_segunda_tentativa',
)

VALID_SUFFIXES = {'.pdf', '.html', '.htm'}


def is_valid_document(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name.lower()
    if path.suffix.lower() not in VALID_SUFFIXES:
        return False
    if any(token in name for token in INVALID_PATTERNS):
        return False
    return True


def cleanup_country(country_dir: Path):
    kept = []
    removed = []
    for child in sorted(country_dir.iterdir()):
        if child.is_dir():
            continue
        name = child.name.lower()
        if is_valid_document(child):
            kept.append(child)
            continue
        if child.suffix.lower() == '.zip' or 'readme' in name or 'log' in name or 'falha' in name or 'indisponivel' in name:
            child.unlink(missing_ok=True)
            removed.append(child.name)
            continue
        if child.suffix.lower() == '.txt':
            child.unlink(missing_ok=True)
            removed.append(child.name)
            continue
        if child.name.lower().startswith('readme'):
            child.unlink(missing_ok=True)
            removed.append(child.name)
            continue
        child.unlink(missing_ok=True)
        removed.append(child.name)

    if not kept:
        try:
            for item in sorted(country_dir.iterdir(), reverse=True):
                if item.is_file():
                    item.unlink(missing_ok=True)
            country_dir.rmdir()
            print(f"Pasta removida: {country_dir.name}")
        except OSError as exc:
            print(f"Não foi possível remover a pasta {country_dir.name}: {exc}")
    elif removed:
        print(f"País mantido: {country_dir.name} | arquivos removidos: {removed}")


def main():
    if not ROOT.exists():
        raise FileNotFoundError(f'Corpus não encontrado em {ROOT}')

    removed_dirs = []
    for child in sorted(ROOT.iterdir()):
        if not child.is_dir():
            continue
        files = [p for p in child.iterdir() if p.is_file()]
        has_valid = any(is_valid_document(p) for p in files)
        if not has_valid:
            for item in sorted(files, reverse=True):
                item.unlink(missing_ok=True)
            try:
                child.rmdir()
                removed_dirs.append(child.name)
                print(f"Pasta removida por ausência de documento válido: {child.name}")
            except OSError as exc:
                print(f"Não foi possível remover a pasta {child.name}: {exc}")
            continue
        cleanup_country(child)

    print('\nPaíses mantidos no corpus:')
    for child in sorted(ROOT.iterdir()):
        if child.is_dir():
            print(f'- {child.name}')

    if removed_dirs:
        print('\nPastas removidas:')
        for name in removed_dirs:
            print(f'- {name}')


if __name__ == '__main__':
    main()
