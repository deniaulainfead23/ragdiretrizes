from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from openai import OpenAI

from rag_project.corpus_registry import analysis_documents, get_country, load_registry
from rag_project.openai_vector_store import DEFAULT_MODEL, _load_manifest, cloud_rag_query
from rag_project.paths import CORPUS_DIR
from rag_project.rag.ingest import extract_pdf_pages

CURRENT_NATIONAL_VECTOR_STORE = "todos_paises_exploratorio_20260927_01_native"


def _normalize(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold()


def _parse_json_object(raw: object) -> dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _resolve_document_id(evidence: dict[str, Any], documents: list[dict[str, Any]]) -> dict[str, Any] | None:
    raw_id = str(evidence.get("document_id") or "").strip()
    raw_title = str(evidence.get("document_title") or evidence.get("document") or "").strip()
    raw_filename = str(evidence.get("filename") or "").strip()
    for document in documents:
        if raw_id and raw_id == str(document.get("document_id", "")).strip():
            return document
    targets = {Path(value).stem.casefold() for value in (raw_title, raw_filename) if value}
    if targets:
        matches = [
            document for document in documents
            if Path(str(document.get("file", ""))).stem.casefold() in targets
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def _check_evidence_source(
    evidence: dict[str, Any],
    country: str,
    documents: list[dict[str, Any]],
    page_cache: dict[str, dict[str, str]],
    position: int = 1,
) -> dict[str, Any]:
    document = _resolve_document_id(evidence, documents)
    excerpt = str(evidence.get("source_text") or evidence.get("trecho_original") or "").strip()
    page_value = evidence.get("page_start") or evidence.get("page") or evidence.get("página") or ""
    result: dict[str, Any] = {
        "country": country,
        "evidence_id": str(evidence.get("evidence_id") or ""),
        "evidence_ref": str(evidence.get("evidence_id") or f"candidate_{position:02d}"),
        "requested_document_id": str(evidence.get("document_id") or ""),
        "document_id": str(document.get("document_id") or "") if document else "",
        "document_title": str(evidence.get("document_title") or evidence.get("document") or ""),
        "page_start": str(page_value),
        "source_text": excerpt,
        "source_registry_status": str(document.get("validation_status") or "") if document else "",
        "source_path": "",
        "citation_status": "unresolved",
        "matched_physical_page": "",
        "reason": "",
    }
    if document is None:
        result["citation_status"] = "document_not_resolved_in_current_registry"
        result["reason"] = "O document_id/título retornado não corresponde unicamente a um documento registrado para este país."
        return result
    pdf_path = CORPUS_DIR / country / str(document.get("file", ""))
    if not pdf_path.is_file():
        result["citation_status"] = "source_pdf_missing"
        result["reason"] = "O PDF registrado não existe no corpus atual."
        return result
    result["source_path"] = pdf_path.relative_to(CORPUS_DIR).as_posix()
    if result["source_path"] not in page_cache:
        try:
            page_cache[result["source_path"]] = {
                str(number): str(text or "")
                for number, text in extract_pdf_pages(str(pdf_path))
            }
        except Exception as exc:
            page_cache[result["source_path"]] = {}
            result["reason"] = f"Falha ao extrair o PDF: {type(exc).__name__}."
    pages = page_cache[result["source_path"]]
    if not pages:
        result["citation_status"] = "pdf_text_unavailable"
        result["reason"] = result["reason"] or "Não foi possível extrair texto do PDF atual."
        return result
    normalized_excerpt = _normalize(excerpt)
    cited_page = str(page_value).strip()
    cited_page_text = pages.get(cited_page, "")
    if not cited_page_text:
        result["citation_status"] = "cited_physical_page_not_extracted"
        result["reason"] = "A página física citada não está disponível no texto extraído do PDF."
        return result
    result["matched_physical_page"] = cited_page
    result["_page_text_for_semantic_review"] = cited_page_text
    if excerpt and normalized_excerpt in _normalize(cited_page_text):
        result["citation_status"] = "exact_text_on_cited_physical_page"
        result["matched_physical_page"] = cited_page
        result["reason"] = "O trecho aparece literalmente, após normalização de espaços, na página física indicada."
        return result
    if not excerpt:
        result["citation_status"] = "source_text_missing_semantic_check_needed"
        result["reason"] = "Não veio trecho literal do RAG; a síntese pode ser comparada com o texto da página citada."
    else:
        result["citation_status"] = "paraphrase_candidate_on_cited_page"
        result["reason"] = "O texto do RAG não é literal na página citada; requer comparação semântica e extração de uma passagem literal de apoio."
    return result


def _judge_semantic_support(
    question: str,
    answer: str,
    verified_evidence: list[dict[str, Any]],
    api_key: str | None,
    model: str,
) -> dict[str, Any]:
    if not verified_evidence:
        return {
            "decision": "doubtful",
            "reason": "Não há evidências com trecho e página conferidos no PDF para julgar o conteúdo da resposta.",
            "supported_claims": [],
            "unsupported_claims": [],
            "claim_reviews": [],
            "citation_reviews": [],
        }
    client = OpenAI(api_key=api_key)
    payload = {
        "question": question,
        "answer_to_check": answer,
        "source_page_candidates": [
            {
                "evidence_ref": item["evidence_ref"],
                "country": item["country"],
                "document_id": item["document_id"],
                "page": item["matched_physical_page"],
                "rag_excerpt_candidate": item["source_text"],
                "source_page_text": item.get("_page_text_for_semantic_review", "")[:7000],
                "source_page_text_truncated": len(item.get("_page_text_for_semantic_review", "")) > 7000,
            }
            for item in verified_evidence
        ],
    }
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você audita uma síntese documental. A resposta e o rag_excerpt_candidate podem parafrasear o documento; "
                    "não exija cópia literal dessas duas coisas. Compare-os somente com source_page_text, sem usar conhecimento externo. "
                    "Para cada source_page_candidate, retorne citation_reviews com evidence_ref, verdict ('literal', "
                    "'paraphrase_supported' ou 'unsupported'), supporting_quote e reason. supporting_quote DEVE ser copiada "
                    "literalmente de source_page_text, sem tradução nem paráfrase. Se o trecho candidato resumir uma ideia da página, "
                    "use paraphrase_supported e forneça a frase original exata que sustenta a ideia. Se não houver suporte, use unsupported. "
                    "Avalie também a resposta integral e retorne um objeto json válido com decision ('supported' ou 'doubtful'), reason, supported_claims, "
                    "unsupported_claims e claim_reviews. Marque doubtful se qualquer afirmação importante não tiver apoio documental."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=700,
    )
    parsed = _parse_json_object(response.choices[0].message.content)
    if parsed.get("decision") not in {"supported", "doubtful"}:
        return {
            "decision": "doubtful",
            "reason": "A revisão semântica não retornou a estrutura esperada.",
            "supported_claims": [],
            "unsupported_claims": [],
            "claim_reviews": [],
            "citation_reviews": [],
        }
    unsupported = parsed.get("unsupported_claims") if isinstance(parsed.get("unsupported_claims"), list) else []
    raw_claim_reviews = parsed.get("claim_reviews") if isinstance(parsed.get("claim_reviews"), list) else []
    claim_reviews = []
    allowed_verdicts = {"supported", "partially_supported", "unsupported"}
    for position, item in enumerate(raw_claim_reviews, start=1):
        if not isinstance(item, dict):
            claim_reviews.append({
                "claim": str(item),
                "verdict": "unclassified",
                "supporting_evidence_ids": [],
                "reason": "O juiz semântico retornou a afirmação sem veredicto estruturado.",
            })
            continue
        verdict = str(item.get("verdict") or "").strip().lower()
        claim_reviews.append({
            "claim": str(item.get("claim") or f"afirmação_{position:02d}"),
            "verdict": verdict if verdict in allowed_verdicts else "unclassified",
            "supporting_evidence_ids": item.get("supporting_evidence_ids") if isinstance(item.get("supporting_evidence_ids"), list) else [],
            "reason": str(item.get("reason") or (
                "O juiz não classificou esta afirmação explicitamente." if verdict not in allowed_verdicts else ""
            )),
        })
    citation_reviews = parsed.get("citation_reviews") if isinstance(parsed.get("citation_reviews"), list) else []
    decision = parsed["decision"]
    if (
        unsupported
        or not claim_reviews
        or any(item.get("verdict") != "supported" for item in claim_reviews)
    ):
        decision = "doubtful"
    return {
        "decision": decision,
        "reason": str(parsed.get("reason") or ""),
        "supported_claims": parsed.get("supported_claims") if isinstance(parsed.get("supported_claims"), list) else [],
        "unsupported_claims": unsupported,
        "claim_reviews": claim_reviews,
        "citation_reviews": citation_reviews,
    }


def _apply_semantic_citation_reviews(
    citations: list[dict[str, Any]],
    semantic: dict[str, Any],
) -> None:
    reviews = {
        str(item.get("evidence_ref") or ""): item
        for item in semantic.get("citation_reviews", [])
        if isinstance(item, dict)
    }
    for citation in citations:
        if citation.get("citation_status") == "exact_text_on_cited_physical_page":
            citation["verified_source_quote"] = citation.get("source_text", "")
            continue
        if citation.get("citation_status") not in {
            "paraphrase_candidate_on_cited_page",
            "source_text_missing_semantic_check_needed",
        }:
            continue
        review = reviews.get(str(citation.get("evidence_ref") or ""), {})
        quote = str(review.get("supporting_quote") or "").strip()
        page_text = str(citation.get("_page_text_for_semantic_review") or "")
        exact_quote_found = bool(quote and _normalize(quote) in _normalize(page_text))
        if review.get("verdict") in {"literal", "paraphrase_supported"} and exact_quote_found:
            citation["citation_status"] = "semantic_paraphrase_supported_by_exact_page_quote"
            citation["verified_source_quote"] = quote
            citation["reason"] = (
                "O trecho retornado pelo RAG é uma paráfrase, mas o juiz encontrou uma passagem literal de apoio "
                "na página física citada e o código confirmou essa passagem no PDF."
            )
        else:
            citation["citation_status"] = "semantic_support_not_verified"
            citation["reason"] = str(review.get("reason") or "Não foi possível confirmar uma passagem literal de apoio na página citada.")
            if quote and not exact_quote_found:
                citation["reason"] += " A frase proposta pelo juiz também não foi localizada literalmente no texto extraído da página."


def validate_rag_answer(
    question: str,
    country: str,
    answer: str | None = None,
    *,
    vector_store_id: str | None = None,
    question_id: str = "Q15",
    category_id: str = "C15",
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    rag_query_fn: Callable[..., str] | None = None,
    semantic_judge_fn: Callable[..., dict[str, Any]] | None = None,
    page_cache: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Executa uma consulta opcional e audita citações no PDF local e suporte semântico.

    O status é preliminar e sempre exige revisão humana. `validado_preliminarmente`
    não significa validação científica final nem aprovação da fonte pelo pesquisador.
    A resposta pode ser uma síntese parafraseada; a conferência literal aplica-se
    somente ao trecho de evidência citado (`source_text`), não à resposta inteira.
    """
    load_dotenv(Path(__file__).resolve().parent / ".env")
    country = str(country or "").strip().lower()
    registry = load_registry()
    country_entry = get_country(registry, country)
    if not country_entry or not country_entry.get("include_in_analysis"):
        raise ValueError(f"País não está ativo no registro do corpus: {country}")
    documents = [
        document for entry, document in analysis_documents(
            registry, country=country, include_pending_review=True
        )
        if entry.get("country") == country
    ]
    if not documents:
        raise ValueError(f"Nenhum documento nacional registrado para: {country}")

    manifest = _load_manifest()
    selected_store = vector_store_id or manifest.get(CURRENT_NATIONAL_VECTOR_STORE, {}).get("vector_store_id")
    if not selected_store:
        raise ValueError("Vector Store nacional atual não encontrado no manifesto local.")
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key and (answer is None or semantic_judge_fn is None):
        raise ValueError("OPENAI_API_KEY necessária para consultar o RAG e executar a revisão semântica.")

    if answer is None:
        query = rag_query_fn or cloud_rag_query
        answer = query(
            selected_store,
            question,
            api_key=key,
            model=model,
            question_id=question_id,
            country=country,
            framework="",
            category_id=category_id,
        )
    parsed_answer = _parse_json_object(answer)
    response_text = parsed_answer.get("response") if isinstance(parsed_answer.get("response"), str) else ""
    evidences = parsed_answer.get("evidences", []) if isinstance(parsed_answer, dict) else []
    if not isinstance(evidences, list):
        evidences = []

    page_cache = page_cache if page_cache is not None else {}
    checks = [
        _check_evidence_source(item, country, documents, page_cache, position)
        for position, item in enumerate(evidences, start=1) if isinstance(item, dict)
    ]
    semantic_candidates = [
        item for item in checks
        if item["citation_status"] in {
            "exact_text_on_cited_physical_page",
            "paraphrase_candidate_on_cited_page",
            "source_text_missing_semantic_check_needed",
        }
    ]
    judge = semantic_judge_fn or _judge_semantic_support
    if response_text.strip():
        try:
            semantic = judge(question, response_text, semantic_candidates, key, model)
        except Exception as exc:
            semantic = {
                "decision": "doubtful",
                "reason": f"Falha na revisão semântica: {type(exc).__name__}: {str(exc)[:400]}",
                "unsupported_claims": [],
                "citation_reviews": [],
            }
    else:
        semantic = {
            "decision": "doubtful",
            "reason": "A resposta RAG não contém uma síntese textual válida.",
            "unsupported_claims": [],
            "citation_reviews": [],
        }
    _apply_semantic_citation_reviews(semantic_candidates, semantic)

    accepted_citation_statuses = {
        "exact_text_on_cited_physical_page",
        "semantic_paraphrase_supported_by_exact_page_quote",
    }
    all_citations_supported = bool(checks) and all(
        item["citation_status"] in accepted_citation_statuses for item in checks
    )
    is_supported = semantic.get("decision") == "supported"
    status = "validado_preliminarmente" if response_text.strip() and all_citations_supported and is_supported else "conteudo_duvidoso"
    reasons = []
    if not parsed_answer:
        reasons.append("A saída RAG não é um objeto JSON legível.")
    if not checks:
        reasons.append("Nenhuma evidência estruturada foi retornada.")
    if checks and not all_citations_supported:
        reasons.append("Uma ou mais citações não foram confirmadas literal ou semanticamente com passagem exata na página física indicada.")
    if semantic.get("decision") != "supported":
        reasons.append(str(semantic.get("reason") or "O suporte semântico não foi confirmado."))

    detailed_reasons: list[dict[str, Any]] = []
    if not parsed_answer:
        detailed_reasons.append({
            "code": "rag_output_not_json",
            "detail": "A saída do RAG não pôde ser interpretada como objeto JSON com resposta e evidências.",
        })
    if not response_text.strip():
        detailed_reasons.append({
            "code": "answer_missing",
            "detail": "Não foi encontrada uma síntese textual para avaliar.",
        })
    if not checks:
        detailed_reasons.append({
            "code": "evidence_missing",
            "detail": "Nenhuma evidência estruturada foi retornada pelo RAG.",
        })
    for check in checks:
        if check["citation_status"] not in accepted_citation_statuses:
            detailed_reasons.append({
                "code": check["citation_status"],
                "evidence_id": check.get("evidence_id", ""),
                "document_id": check.get("document_id", "") or check.get("requested_document_id", ""),
                "cited_page": check.get("page_start", ""),
                "matched_physical_page": check.get("matched_physical_page", ""),
                "detail": check.get("reason", "A citação precisa de conferência."),
            })
    for claim in semantic.get("claim_reviews", []):
        if isinstance(claim, dict) and claim.get("verdict") != "supported":
            detailed_reasons.append({
                "code": "claim_not_fully_supported",
                "claim": claim.get("claim", ""),
                "evidence_ids": claim.get("supporting_evidence_ids", []),
                "detail": claim.get("reason") or "A afirmação precisa ser restringida ou reformulada.",
            })
    if semantic.get("decision") != "supported" and not any(
        item.get("code") == "claim_not_fully_supported" for item in detailed_reasons
    ):
        detailed_reasons.append({
            "code": "semantic_support_not_confirmed",
            "detail": semantic.get("reason") or "O suporte semântico não foi confirmado.",
        })

    if status == "validado_preliminarmente":
        result_description = (
            "A síntese pode parafrasear a fonte. Cada evidência citada foi confirmada literalmente na página "
            "ou, quando o trecho do RAG era uma paráfrase, o juiz encontrou uma passagem literal de apoio na página "
            "e o código confirmou essa passagem no PDF. A revisão semântica automática considerou as afirmações sustentadas. "
            "Ainda requer aprovação humana."
        )
    else:
        result_description = (
            "A resposta não passou na checagem automática. Consulte os motivos por evidência e por afirmação; "
            "corrija a citação ou restrinja/reformule a síntese antes de usá-la."
        )

    human_actions = [
        "Confirmar autoria, publicação oficial, país e versão do documento no escopo da pesquisa.",
        "Conferir visualmente no PDF a página física e mapear separadamente o número impresso.",
        "Ler o parágrafo/seção ao redor do trecho e confirmar que sustenta a afirmação, não apenas palavras semelhantes.",
        "Revisar a tradução quando a fonte não estiver em português e manter o trecho original separado.",
    ]
    if detailed_reasons:
        human_actions.insert(0, "Resolver cada motivo listado em status_reasons; não aprovar a resposta enquanto houver citação não localizada ou afirmação sem suporte.")

    # The full page is sent to the semantic judge, but the report only needs the verified quote.
    for check in checks:
        check.pop("_page_text_for_semantic_review", None)

    return {
        "question_id": question_id,
        "country": country,
        "question": question,
        "answer": response_text,
        "status": status,
        "result_description": result_description,
        "validation_level": "automatic_preliminary",
        "human_review_required": True,
        "vector_store_id": selected_store,
        "source_validation_note": "Status de curadoria exibido por evidência; a função não promove status no registro.",
        "citation_checks": checks,
        "semantic_review": semantic,
        "reasons": reasons,
        "status_reasons": detailed_reasons,
        "human_review_checklist": human_actions,
        "raw_rag_response": str(answer),
    }


def format_validation_report(result: dict[str, Any]) -> str:
    """Render a validation result as a readable plain-text report."""
    status_labels = {
        "validado_preliminarmente": "VALIDADO PRELIMINARMENTE",
        "conteudo_duvidoso": "CONTEÚDO DUVIDOSO",
    }
    lines = [
        "RELATÓRIO DE AUDITORIA DA RESPOSTA RAG",
        "=" * 42,
        f"Status: {status_labels.get(result.get('status', ''), result.get('status', 'não informado'))}",
        f"Nível: {result.get('validation_level', 'não informado')}",
        f"Revisão humana necessária: {'SIM' if result.get('human_review_required', True) else 'NÃO'}",
        f"País: {result.get('country', 'não informado')}",
        f"ID da pergunta: {result.get('question_id', 'não informado')}",
        "",
        "PERGUNTA",
        str(result.get('question') or '(não informada)'),
        "",
        "RESPOSTA SINTETIZADA PELO RAG",
        str(result.get('answer') or '(vazia ou não interpretável)'),
        "",
        "DESCRIÇÃO DO RESULTADO",
        str(result.get('result_description') or '(sem descrição)'),
        "",
        "CHECAGEM DAS CITAÇÕES NO PDF",
    ]
    checks = result.get("citation_checks") or []
    if not checks:
        lines.append("Nenhuma evidência estruturada foi retornada pelo RAG.")
    for index, check in enumerate(checks, start=1):
        lines.extend([
            f"{index}. Evidência: {check.get('evidence_id') or check.get('evidence_ref') or '(sem ID)'}",
            f"   Resultado: {check.get('citation_status', 'não verificado')}",
            f"   Documento: {check.get('document_id') or check.get('requested_document_id') or '(não resolvido)'}",
            f"   Página citada: {check.get('page_start') or '(não informada)'}",
        ])
        if check.get("matched_physical_page"):
            lines.append(f"   Página física correspondente: {check['matched_physical_page']}")
        if check.get("source_path"):
            lines.append(f"   Arquivo: {check['source_path']}")
        lines.append(f"   Curadoria do documento: {check.get('source_registry_status') or 'não informada'}")
        lines.append(f"   Motivo: {check.get('reason') or 'sem detalhe'}")
        if check.get("source_text"):
            lines.append(f"   Trecho citado: {check['source_text']}")
        if check.get("verified_source_quote") and check.get("citation_status") == "semantic_paraphrase_supported_by_exact_page_quote":
            lines.append(f"   Passagem literal de apoio localizada no PDF: {check['verified_source_quote']}")

    semantic = result.get("semantic_review") or {}
    lines.extend([
        "",
        "REVISÃO SEMÂNTICA AUTOMÁTICA",
        f"Decisão: {semantic.get('decision') or 'não realizada'}",
        f"Justificativa: {semantic.get('reason') or 'sem detalhe'}",
    ])
    for claim in semantic.get("claim_reviews") or []:
        if isinstance(claim, dict):
            lines.append(
                f"- Afirmação ({claim.get('verdict', 'sem classificação')}): "
                f"{claim.get('claim', '')}"
            )
            if claim.get("reason"):
                lines.append(f"  Motivo: {claim['reason']}")
            if claim.get("supporting_evidence_ids"):
                lines.append(f"  Evidências: {', '.join(map(str, claim['supporting_evidence_ids']))}")

    lines.extend(["", "MOTIVOS DO STATUS"])
    for item in result.get("status_reasons") or []:
        if isinstance(item, dict):
            where = ", ".join(
                f"{key}={item[key]}" for key in ("evidence_id", "document_id", "cited_page", "matched_physical_page")
                if item.get(key) not in (None, "", [])
            )
            prefix = f"[{item.get('code', 'motivo')}] "
            lines.append(prefix + (where + ": " if where else "") + str(item.get("detail") or ""))
        else:
            lines.append(f"- {item}")
    if not (result.get("status_reasons") or result.get("reasons")):
        lines.append("Nenhuma divergência automática identificada; ainda requer revisão humana.")

    lines.extend(["", "CHECKLIST PARA REVISÃO HUMANA"])
    for action in result.get("human_review_checklist") or []:
        lines.append(f"[ ] {action}")
    lines.extend([
        "",
        "Observação: resposta RAG pode ser uma paráfrase. A citação source_text deve ser literal no PDF. "
        "Esta auditoria é preliminar e não substitui a decisão da pesquisadora.",
    ])
    return "\n".join(lines)


def validate_rag_answer_text(*args, **kwargs) -> str:
    """Validate a RAG answer and return a human-readable plain-text report."""
    return format_validation_report(validate_rag_answer(*args, **kwargs))


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita resposta RAG contra PDFs nacionais do corpus.")
    parser.add_argument("--country", required=True, help="Slug do país, por exemplo brasil ou australia")
    parser.add_argument("--question", required=True, help="Pergunta enviada ao RAG")
    parser.add_argument("--answer", default=None, help="Resposta JSON existente; se omitida, executa uma consulta RAG")
    parser.add_argument("--vector-store-id", default=None, help="Padrão: Vector Store nacional atual do manifesto")
    parser.add_argument("--question-id", default="Q15")
    parser.add_argument("--category-id", default="C15")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", default=None, help="Opcional: caminho .txt para salvar o relatório legível")
    args = parser.parse_args()
    result = validate_rag_answer(
        args.question,
        args.country,
        answer=args.answer,
        vector_store_id=args.vector_store_id,
        question_id=args.question_id,
        category_id=args.category_id,
        model=args.model,
    )
    serialized = format_validation_report(result)
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
