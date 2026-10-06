"""Passo 4: perguntar ao RAG. A resposta vem com trechos literais dos documentos."""
from __future__ import annotations

import json
import os
from datetime import datetime

import yaml

from . import caminhos
from .extracao import ler_manifesto
from .indexacao import cliente, ler_indice

INSTRUCOES = (
    "Você responde perguntas usando SOMENTE os documentos recuperados pela busca em arquivos. "
    "Não use conhecimento externo. Responda em português.\n"
    "Regras:\n"
    "1. Cada afirmação da resposta deve estar apoiada em pelo menos um trecho listado em 'evidencias'.\n"
    "2. Cada 'trecho' deve ser copiado LITERALMENTE do documento, no idioma original, sem traduzir, "
    "sem resumir, sem corrigir e sem reticências. Use de uma a três frases contíguas.\n"
    "3. Em 'arquivo', informe o nome do arquivo de onde o trecho foi copiado (ex.: d1a2b3c4d5e.txt).\n"
    "4. Não cite números de página.\n"
    "5. Se os documentos não tratarem do assunto, devolva encontrou_resposta=false, explique em "
    "'resposta' que o corpus não traz a informação e deixe 'evidencias' vazia."
)

ESQUEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["encontrou_resposta", "resposta", "evidencias"],
    "properties": {
        "encontrou_resposta": {"type": "boolean"},
        "resposta": {"type": "string"},
        "evidencias": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["arquivo", "trecho"],
                "properties": {"arquivo": {"type": "string"}, "trecho": {"type": "string"}},
            },
        },
    },
}


def carregar_perguntas() -> list[dict]:
    dados = yaml.safe_load(caminhos.PERGUNTAS.read_text(encoding="utf-8")) or {}
    return dados.get("perguntas", [])


def pastas_do_corpus() -> list[str]:
    return sorted({r["pasta"] for r in ler_manifesto() if r["situacao"] == "ok" and r["pasta"]})


def perguntar(pergunta: str, pasta: str = "", api=None) -> dict:
    """Faz uma pergunta ao Vector Store. `pasta` restringe a busca a uma subpasta do corpus."""
    indice = ler_indice()
    if not indice.get("vector_store_id"):
        raise RuntimeError("O corpus ainda não foi indexado (passo 3).")
    api = api or cliente()
    modelo = os.environ.get("RAG_MODELO", "gpt-4o-mini")
    busca = {
        "type": "file_search",
        "vector_store_ids": [indice["vector_store_id"]],
        "max_num_results": int(os.environ.get("RAG_MAX_TRECHOS", "12")),
    }
    if pasta:
        busca["filters"] = {"type": "eq", "key": "pasta", "value": pasta}

    resposta = api.responses.create(
        model=modelo,
        instructions=INSTRUCOES,
        input=pergunta,
        tools=[busca],
        tool_choice="required",
        temperature=0,
        text={"format": {"type": "json_schema", "name": "resposta_rag", "schema": ESQUEMA, "strict": True}},
    )
    try:
        dados = json.loads(resposta.output_text)
    except (json.JSONDecodeError, TypeError):
        dados = {"encontrou_resposta": False, "resposta": str(resposta.output_text or ""), "evidencias": []}

    origem = {r["doc_id"]: r["origem"] for r in ler_manifesto()}
    evidencias = []
    for ev in dados.get("evidencias", []):
        doc_id = str(ev.get("arquivo", "")).strip().removesuffix(".txt")
        evidencias.append({
            "doc_id": doc_id if doc_id in origem else "",
            "documento": origem.get(doc_id, str(ev.get("arquivo", ""))),
            "trecho": str(ev.get("trecho", "")).strip(),
        })
    return {
        "pergunta": pergunta,
        "pasta": pasta,
        "modelo": modelo,
        "encontrou_resposta": bool(dados.get("encontrou_resposta")),
        "resposta": str(dados.get("resposta", "")).strip(),
        "evidencias": evidencias,
    }


def rodar(perguntas: list[dict], pasta: str = "", avisar=print, api=None) -> str:
    """Roda uma lista de perguntas ({id, titulo, pergunta}) e grava uma rodada em dados_derivados/respostas."""
    api = api or cliente()
    caminhos.RESPOSTAS.mkdir(parents=True, exist_ok=True)
    rodada = datetime.now().strftime("%Y%m%d-%H%M%S") + (f"_{pasta}" if pasta else "")
    destino = caminhos.RESPOSTAS / f"{rodada}.json"
    itens = []
    for n, p in enumerate(perguntas, start=1):
        avisar(f"[{n}/{len(perguntas)}] {p.get('id', '')} {p['pergunta'][:90]}")
        try:
            item = perguntar(p["pergunta"], pasta=pasta, api=api)
        except Exception as exc:
            avisar(f"   FALHOU: {type(exc).__name__}: {exc}")
            continue
        item = {"id": p.get("id", f"P{n:02d}"), "titulo": p.get("titulo", ""), **item}
        itens.append(item)
        destino.write_text(
            json.dumps({"rodada": rodada, "vector_store_id": ler_indice().get("vector_store_id"), "itens": itens},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return rodada
