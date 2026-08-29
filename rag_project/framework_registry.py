from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / 'config'
FRAMEWORK_DIR = ROOT / 'framework'


_DEFAULT_RULES: dict[str, Any] = {
    'version': '2.0',
    'lowercase': True,
    'strip_accents': True,
    'remove_punctuation': True,
    'remove_page_numbers': True,
    'split_on_whitespace': True,
    'preserve_hyphenated_terms': False,
    'stopwords': {
        'language': ['the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for', 'on', 'with', 'as', 'by', 'is', 'are', 'be', 'this', 'that'],
        'documental': ['sobre', 'todos', 'documento', 'currículo', 'curriculo', 'educação', 'educacao', 'país', 'pais', 'área', 'area', 'capítulo', 'capitulo'],
    },
    'min_token_length': 2,
    'allow_bigram_detection': True,
}


_FRAMEWORKS: dict[str, dict[str, Any]] = {
    'UNESCO_GCED_2015': {
        'framework_id': 'UNESCO_GCED_2015',
        'title': 'UNESCO Global Citizenship Education (GCED)',
        'version': '2.0',
        'source': 'UNESCO',
        'dimensions': [
            {
                'code': 'COG',
                'name': 'Cognitive',
                'keywords': [
                    'thinking', 'critical thinking', 'analysis', 'problem solving', 'understanding', 'global issues',
                    'pensamento crítico', 'pensamento critico', 'resolução de problemas', 'resolucao de problemas',
                    'análise', 'analise', 'compreensão', 'compreensao', 'questões globais', 'questoes globais'
                ],
            },
            {
                'code': 'SOE',
                'name': 'Socioemotional',
                'keywords': [
                    'empathy', 'respect', 'solidarity', 'relationships', 'identity', 'social responsibility',
                    'empatia', 'respeito', 'solidariedade', 'relações', 'relacoes', 'identidade', 'responsabilidade social'
                ],
            },
            {
                'code': 'BEH',
                'name': 'Behavioral',
                'keywords': [
                    'participation', 'action', 'responsible action', 'engagement', 'citizenship', 'behavior',
                    'participação', 'participacao', 'ação', 'acao', 'envolvimento', 'cidadania', 'comportamento'
                ],
            },
        ],
        'notes': 'Framework analítico de referência para educação para a cidadania global.',
    },
    'COMPUTING_AND_DIGITAL_EDUCATION': {
        'framework_id': 'COMPUTING_AND_DIGITAL_EDUCATION',
        'title': 'Computing and Digital Education',
        'version': '2.0',
        'source': 'Curricular comparison',
        'domains': [
            {'code': 'COMP', 'name': 'Computing', 'keywords': ['computational thinking', 'programming', 'algorithms', 'logic', 'coding', 'abstraction']},
            {'code': 'DIG', 'name': 'Digital Literacy', 'keywords': ['digital literacy', 'technology use', 'information literacy', 'digital citizenship', 'digital skills']},
            {'code': 'ETH', 'name': 'Ethics and Safety', 'keywords': ['digital ethics', 'online safety', 'responsible use', 'privacy', 'cybersecurity']},
        ],
        'notes': 'Framework analítico para competências de computação e educação digital.',
    },
    'UNESCO_FUTURES_2021': {
        'framework_id': 'UNESCO_FUTURES_2021',
        'title': 'UNESCO Futures of Education',
        'version': '2.0',
        'source': 'UNESCO',
        'dimensions': [
            {'code': 'FUT', 'name': 'Futures', 'keywords': ['future', 'transformation', 'resilience', 'sustainability', 'learning to learn']},
        ],
        'notes': 'Framework complementar para análise de futuro, inovação e aprendizagem.',
    },
}


def get_framework_by_id(framework_id: str) -> dict[str, Any] | None:
    return _FRAMEWORKS.get(framework_id)


def list_frameworks() -> list[str]:
    return sorted(_FRAMEWORKS.keys())


def load_preprocessing_rules() -> dict[str, Any]:
    path = CONFIG_DIR / 'preprocessing_rules.yaml'
    if path.exists():
        with path.open('r', encoding='utf-8') as handle:
            loaded = yaml.safe_load(handle) or {}
        if isinstance(loaded, dict):
            merged = _DEFAULT_RULES.copy()
            merged.update(loaded)
            return merged
    return _DEFAULT_RULES.copy()


def load_stopwords(kind: str) -> set[str]:
    normalized = str(kind).strip().lower()
    mapping = {
        'language': 'stopwords_language.txt',
        'documental': 'stopwords_documental.txt',
        'default': 'stopwords_language.txt',
    }
    path = CONFIG_DIR / mapping.get(normalized, 'stopwords_language.txt')
    if not path.exists():
        default = _DEFAULT_RULES.get('stopwords', {}).get(normalized, [])
        return set(str(token).lower() for token in default)

    tokens: set[str] = set()
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            token = line.strip().lower()
            if token and not token.startswith('#'):
                tokens.add(token)
    return tokens


def load_excluded_entities() -> set[str]:
    path = CONFIG_DIR / 'excluded_entities.txt'
    if not path.exists():
        return {
            'documento',
            'currículo',
            'curriculo',
            'educação',
            'educacao',
            'país',
            'pais',
            'área',
            'area',
        }

    entities: set[str] = set()
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            token = line.strip().lower()
            if token and not token.startswith('#'):
                entities.add(token)
    return entities


def export_framework_csvs() -> dict[str, Path]:
    FRAMEWORK_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    alias_map = {
        'UNESCO_GCED_2015': 'unesco_framework.csv',
        'COMPUTING_AND_DIGITAL_EDUCATION': 'computing_framework.csv',
        'UNESCO_FUTURES_2021': 'unesco_futures_framework.csv',
    }

    for framework_id, data in _FRAMEWORKS.items():
        rows: list[dict[str, str]] = []
        for block in data.get('dimensions', data.get('domains', [])):
            rows.append({
                'framework_id': framework_id,
                'code': str(block.get('code', '')),
                'name': str(block.get('name', '')),
                'keywords': '; '.join(str(item) for item in block.get('keywords', [])),
            })

        import csv
        preferred_name = alias_map.get(framework_id, f'{framework_id.lower()}.csv')
        csv_path = FRAMEWORK_DIR / preferred_name
        with csv_path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['framework_id', 'code', 'name', 'keywords'])
            writer.writeheader()
            writer.writerows(rows)
        outputs[framework_id] = csv_path

        # mantém compatibilidade com o nome técnico antigo também
        legacy_path = FRAMEWORK_DIR / f'{framework_id.lower()}.csv'
        if legacy_path != csv_path:
            with legacy_path.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=['framework_id', 'code', 'name', 'keywords'])
                writer.writeheader()
                writer.writerows(rows)
            outputs[f'{framework_id}_legacy'] = legacy_path
    return outputs
