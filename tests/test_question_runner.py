from rag_project.run_questions_by_country import (
    _parse_response,
    _response_text,
    build_country_question_plan,
)


def test_country_question_plan_reuses_retrieval_questions_for_country():
    plan = build_country_question_plan('brasil')
    assert plan
    assert all(item['target_country'] in {None, 'brasil'} for item in plan)
    assert any(item['question_id'] == 'Q01' for item in plan)
    assert all(item['question_type'] == 'evidence_retrieval' for item in plan if item['question_id'] in {'Q01'})


def test_parse_response_recovers_literal_control_characters_in_json():
    payload = '{"question_id":"Q02","response":"A\tB","evidences":[{"source_text":"x\t-y"}]}'

    parsed = _parse_response(payload)

    assert parsed['question_id'] == 'Q02'
    assert parsed['response'] == 'A\tB'
    assert parsed['evidences'] == [{'source_text': 'x\t-y'}]


def test_empty_response_gets_explanation_without_claiming_absence():
    text = _response_text({'response': '', 'evidences': []}, has_evidence=False)

    assert text
    assert 'não indica ausência do tema' in text


def test_empty_synthesis_with_evidence_points_to_evidence_review():
    text = _response_text({'response': '', 'evidences': [{'source_text': 'trecho'}]}, has_evidence=True)

    assert text
    assert 'não foi gerada uma síntese textual' in text
