from rag_project.run_questions_by_country import build_country_question_plan


def test_country_question_plan_reuses_retrieval_questions_for_country():
    plan = build_country_question_plan('brasil')
    assert plan
    assert all(item['target_country'] in {None, 'brasil'} for item in plan)
    assert any(item['question_id'] == 'Q22' for item in plan)
    assert all(item['question_type'] == 'evidence_retrieval' for item in plan if item['question_id'] in {'Q22'})
