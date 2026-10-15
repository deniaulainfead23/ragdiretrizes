from rag_project.run_questions_by_country import (
    _parse_response,
    _response_text,
    _structured_question_text,
    build_country_question_plan,
)


def test_country_question_plan_reuses_retrieval_questions_for_country():
    plan = build_country_question_plan('brasil')
    assert plan
    assert all(item['target_country'] in {None, 'brasil'} for item in plan)
    assert any(item['question_id'] == 'Q01' for item in plan)
    assert all(item['question_type'] == 'evidence_retrieval' for item in plan if item['question_id'] in {'Q01'})


def test_dlgf_question_passes_official_areas_to_the_prompt():
    item = next(
        item for item in build_country_question_plan('brasil')
        if item['question_id'] == 'Q04'
    )

    prompt = _structured_question_text(item, 'brasil')

    assert 'dispositivos e software' in prompt
    assert 'informação e dados' in prompt
    assert 'competências relacionadas à carreira' in prompt
    assert item['exclusion_rule'] in prompt


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


def test_non_text_synthesis_is_not_serialized_as_a_python_object():
    text = _response_text(
        {'response': {'areas': [{'area': 'Digital Citizenship'}]}},
        has_evidence=True,
    )

    assert 'formato incompatível' in text
    assert 'Digital Citizenship' not in text
