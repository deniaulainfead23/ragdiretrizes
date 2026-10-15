from rag_project.question_catalog import get_questions, validate_question


def test_questions_yaml_has_structured_schema():
    questions = get_questions()
    assert questions
    assert {'question_id', 'question_text', 'question_type', 'analysis_stage', 'framework', 'category_id', 'version'}.issubset(questions[0].keys())
    for question in questions:
        validate_question(question)


def test_retrieval_questions_are_not_rankings():
    questions = get_questions()
    retrieval = [q for q in questions if q['question_type'] == 'evidence_retrieval']
    assert retrieval
    for question in retrieval:
        text = question['question_text'].lower()
        assert 'maior alinhamento' not in text
        assert 'mais próximo' not in text
        assert 'melhor' not in text
