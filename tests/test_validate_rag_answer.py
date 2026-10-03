import json
from pathlib import Path
from types import SimpleNamespace

import rag_project.validate_rag_answer as validator
from rag_project.validate_rag_answer import format_validation_report


COUNTRY_ENTRY = {'country': 'brasil', 'include_in_analysis': True}
DOCUMENT = {
    'document_id': 'BR_001',
    'file': 'documento.pdf',
    'validation_status': 'pending_review',
    'role': 'primary',
}
SOURCE_TEXT = 'A habilidade curricular desenvolve pensamento computacional e resolução de problemas.'


def setup_validator(monkeypatch, tmp_path, excerpt=SOURCE_TEXT, page=1):
    country_dir = tmp_path / 'brasil'
    country_dir.mkdir()
    (country_dir / 'documento.pdf').write_bytes(b'fake pdf for mocked extraction')
    monkeypatch.setattr(validator, 'CORPUS_DIR', tmp_path)
    monkeypatch.setattr(validator, 'load_registry', lambda: {'countries': [COUNTRY_ENTRY]})
    monkeypatch.setattr(validator, 'get_country', lambda registry, country: COUNTRY_ENTRY)
    monkeypatch.setattr(
        validator,
        'analysis_documents',
        lambda registry, country=None, include_pending_review=False: [(COUNTRY_ENTRY, DOCUMENT)],
    )
    monkeypatch.setattr(validator, '_load_manifest', lambda: {
        validator.CURRENT_NATIONAL_VECTOR_STORE: {'vector_store_id': 'vs-national-test'}
    })
    monkeypatch.setattr(validator, 'extract_pdf_pages', lambda path: [(1, SOURCE_TEXT), (2, 'Outro conteúdo da página dois.')])

    rag_result = json.dumps({
        'question_id': 'Q15',
        'country': 'brasil',
        'response': 'O currículo desenvolve pensamento computacional e resolução de problemas.',
        'evidences': [{
            'evidence_id': 'EVID-1',
            'document_id': 'BR_001',
            'document_title': 'Documento brasileiro',
            'page_start': page,
            'page_end': page,
            'source_text': excerpt,
            'validation_status': 'candidate',
        }],
        'validation_status': 'candidate',
    }, ensure_ascii=False)
    return lambda *args, **kwargs: rag_result


def test_answer_is_only_preliminarily_validated_with_exact_page_and_semantic_support(monkeypatch, tmp_path):
    rag_query = setup_validator(monkeypatch, tmp_path)
    semantic_calls = []

    def semantic_judge(question, answer, evidence, api_key, model):
        semantic_calls.append(evidence)
        return {
            'decision': 'supported',
            'reason': 'A síntese parafraseia o trecho sem ampliar seu sentido.',
            'supported_claims': ['O currículo aborda CT e resolução de problemas.'],
            'unsupported_claims': [],
            'claim_reviews': [{
                'claim': 'O currículo desenvolve pensamento computacional e resolução de problemas.',
                'verdict': 'supported',
                'supporting_evidence_ids': ['EVID-1'],
                'reason': 'Paráfrase sustentada pelo trecho original.',
            }],
        }

    result = validator.validate_rag_answer(
        'O que o currículo desenvolve?',
        'brasil',
        rag_query_fn=rag_query,
        semantic_judge_fn=semantic_judge,
    )

    assert result['status'] == 'validado_preliminarmente'
    assert result['human_review_required'] is True
    assert result['citation_checks'][0]['citation_status'] == 'exact_text_on_cited_physical_page'
    assert result['citation_checks'][0]['source_registry_status'] == 'pending_review'
    assert 'pode parafrasear' in result['result_description']
    assert result['semantic_review']['claim_reviews'][0]['verdict'] == 'supported'
    assert result['human_review_required'] is True
    assert len(semantic_calls[0]) == 1


def test_wrong_page_or_nonmatching_excerpt_is_doubtful(monkeypatch, tmp_path):
    rag_query = setup_validator(monkeypatch, tmp_path, excerpt='Trecho que não existe no PDF.', page=1)
    semantic_calls = []

    def semantic_judge(question, answer, evidence, api_key, model):
        semantic_calls.append([
            {
                'citation_status': item['citation_status'],
                'matched_physical_page': item['matched_physical_page'],
            }
            for item in evidence
        ])
        return {'decision': 'supported', 'reason': 'Saída de teste.', 'unsupported_claims': []}

    result = validator.validate_rag_answer(
        'O que o currículo desenvolve?',
        'brasil',
        rag_query_fn=rag_query,
        semantic_judge_fn=semantic_judge,
    )

    assert result['status'] == 'conteudo_duvidoso'
    assert result['citation_checks'][0]['citation_status'] == 'semantic_support_not_verified'
    assert result['status_reasons'][0]['code'] == 'semantic_support_not_verified'
    assert result['human_review_checklist']
    assert len(semantic_calls[0]) == 1
    assert semantic_calls[0][0]['citation_status'] == 'paraphrase_candidate_on_cited_page'
    assert semantic_calls[0][0]['matched_physical_page'] == '1'


def test_invalid_rag_json_is_doubtful(monkeypatch, tmp_path):
    setup_validator(monkeypatch, tmp_path)

    result = validator.validate_rag_answer(
        'Pergunta?',
        'brasil',
        rag_query_fn=lambda *args, **kwargs: 'resposta não estruturada',
        semantic_judge_fn=lambda *args, **kwargs: {'decision': 'supported'},
    )

    assert result['status'] == 'conteudo_duvidoso'
    assert result['citation_checks'] == []
    assert any('JSON legível' in reason for reason in result['reasons'])


def test_paraphrased_excerpt_is_supported_only_when_exact_quote_is_found(monkeypatch, tmp_path):
    paraphrase = 'Os alunos aprendem CT para resolver desafios curriculares.'
    rag_query = setup_validator(monkeypatch, tmp_path, excerpt=paraphrase, page=1)

    def semantic_judge(question, answer, evidence, api_key, model):
        assert evidence[0]['citation_status'] == 'paraphrase_candidate_on_cited_page'
        return {
            'decision': 'supported',
            'reason': 'A síntese corresponde ao sentido do trecho original.',
            'supported_claims': [answer],
            'unsupported_claims': [],
            'claim_reviews': [{'claim': answer, 'verdict': 'supported', 'reason': 'Apoiado no trecho.'}],
            'citation_reviews': [{
                'evidence_ref': 'EVID-1',
                'verdict': 'paraphrase_supported',
                'supporting_quote': SOURCE_TEXT,
                'reason': 'A página descreve CT e resolução de problemas.',
            }],
        }

    result = validator.validate_rag_answer(
        'O que o currículo desenvolve?',
        'brasil',
        rag_query_fn=rag_query,
        semantic_judge_fn=semantic_judge,
    )

    assert result['status'] == 'validado_preliminarmente'
    assert result['citation_checks'][0]['citation_status'] == 'semantic_paraphrase_supported_by_exact_page_quote'
    assert result['citation_checks'][0]['verified_source_quote'] == SOURCE_TEXT


def test_plain_text_report_explains_status_citations_and_human_actions():
    report = format_validation_report({
        'question_id': 'Q02',
        'country': 'brasil',
        'question': 'Como o currículo trata CT?',
        'answer': 'O currículo inclui CT para resolução de problemas.',
        'status': 'conteudo_duvidoso',
        'result_description': 'Há citação com página divergente.',
        'human_review_required': True,
        'citation_checks': [{
            'evidence_id': 'E1',
            'citation_status': 'exact_text_on_different_physical_page',
            'document_id': 'BR_001',
            'page_start': '8',
            'matched_physical_page': '9',
            'reason': 'O trecho aparece em outra página.',
            'source_text': 'trecho original',
        }],
        'semantic_review': {
            'decision': 'doubtful',
            'reason': 'A citação não sustenta a síntese na página indicada.',
            'claim_reviews': [],
        },
        'status_reasons': [{
            'code': 'exact_text_on_different_physical_page',
            'evidence_id': 'E1',
            'document_id': 'BR_001',
            'cited_page': '8',
            'matched_physical_page': '9',
            'detail': 'Corrigir o localizador.',
        }],
        'human_review_checklist': ['Conferir página impressa e página física.'],
    })

    assert 'Status: CONTEÚDO DUVIDOSO' in report
    assert 'BR_001' in report
    assert 'Página física correspondente: 9' in report
    assert '[ ] Conferir página impressa e página física.' in report
    assert 'source_text deve ser literal' in report
    assert '"status"' not in report
