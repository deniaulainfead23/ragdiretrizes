from __future__ import annotations

import yaml
from pathlib import Path


def get_question_file() -> Path:
    root = Path(__file__).resolve().parent
    return root / 'questions' / 'questions.yaml'


def load_questions() -> list[dict]:
    path = get_question_file()
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8') as handle:
        raw = yaml.safe_load(handle) or {}
    return raw.get('questions', [])


def get_questions() -> list[dict]:
    questions = load_questions()
    for question in questions:
        validate_question(question)
    return questions


def get_question_by_id(question_id: str) -> dict | None:
    for question in get_questions():
        if question.get('question_id') == question_id:
            return question
    return None


def get_retrieval_questions_for_country(country: str | None = None) -> list[dict]:
    questions = get_questions()
    selected = [q for q in questions if q.get('question_type') == 'evidence_retrieval']
    if country is None:
        return selected
    country_key = str(country).lower()
    return [q for q in selected if q.get('target_country') in {None, country, country_key}]


def get_validated_comparison_questions() -> list[dict]:
    return [q for q in get_questions() if q.get('question_type') == 'validated_comparison']


def validate_question(question: dict) -> None:
    required = {
        'question_id', 'title', 'question_text', 'question_type', 'analysis_stage',
        'framework', 'category_id', 'target_scope', 'required_metadata',
        'expected_output', 'evidence_rule', 'exclusion_rule',
        'allow_cross_country_comparison', 'requires_validated_evidence', 'version'
    }
    missing = sorted(required - set(question.keys()))
    if missing:
        raise ValueError(f'Question missing required keys: {missing}')

    if question['question_type'] == 'evidence_retrieval':
        required_fields = {
            'document_id', 'country', 'document_title', 'page_start',
            'page_end', 'chunk_id', 'source_text'
        }
        if not required_fields.issubset(set(question.get('required_metadata', []))):
            raise ValueError(
                f"Question {question['question_id']} does not declare required evidence metadata"
            )

    if question['analysis_stage'] == 'comparison' and question.get('requires_validated_evidence') is not True:
        raise ValueError(
            f"Question {question['question_id']} is a comparison question but requires_validated_evidence is not true"
        )

    if question['question_type'] == 'validated_comparison' and question.get('requires_validated_evidence') is not True:
        raise ValueError(
            f"Question {question['question_id']} invalid validated comparison configuration"
        )

    text = question.get('question_text', '').lower()
    if 'maior alinhamento' in text or 'mais próximo' in text or 'melhor' in text:
        raise ValueError(
            f"Question {question['question_id']} is a ranking-style question and is not allowed"
        )

    if question.get('analysis_stage') == 'comparison' and not question.get('allow_cross_country_comparison', False):
        raise ValueError(
            f"Question {question['question_id']} comparison should allow cross-country comparison"
        )

    allowed_frameworks = {
        'COMPUTING_AND_DIGITAL_EDUCATION',
        'UNESCO_GCED_2015',
        'UNESCO_FUTURES_2021',
        'OECD_PISA',
    }
    if question.get('framework') not in allowed_frameworks:
        raise ValueError(
            f"Question {question['question_id']} has invalid framework name: {question.get('framework')}"
        )
