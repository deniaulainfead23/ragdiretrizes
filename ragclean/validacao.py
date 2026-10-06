"""Passo 5: validar as respostas pelo CONTEÚDO dos documentos originais (sem número de página).

Uma resposta é VALIDADA quando:
  1. pelo menos um trecho citado é localizado no texto do documento original do corpus; e
  2. o juiz semântico confirma que a resposta é sustentada pelas passagens localizadas.

A localização tolera diferenças de quebra de linha, hifenização, aspas e pequenos ruídos de
extração, mas nunca usa página: o trecho é procurado no documento inteiro.
"""
from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from functools import lru_cache

from . import caminhos
from .extracao import ler_manifesto, sha256_arquivo
from .indexacao import cliente

LIMIAR_APROXIMADO = 90  # similaridade mínima (0-100) para aceitar um trecho não idêntico
MIN_TRECHO = 25  # trechos menores que isso são genéricos demais para servir de prova
JANELA = 500  # caracteres de contexto, antes e depois, entregues ao juiz

_TROCAS = str.maketrans({
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‘": "'", "’": "'", "`": "'", "´": "'",
    "–": "-", "—": "-", "‐": "-", "‑": "-", "−": "-", "­": "", "​": "", "﻿": "",
})


def limpar(texto: str) -> str:
    """Normaliza o texto para comparação: Unicode, aspas, travessões, hifenização e espaços."""
    texto = unicodedata.normalize("NFKC", str(texto or "")).translate(_TROCAS)
    texto = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)  # pala-\nvra -> palavra
    return re.sub(r"\s+", " ", texto).strip()


def _partes(trecho: str) -> list[str]:
    """Um trecho com reticências vira várias partes, cada uma conferida separadamente."""
    partes = [limpar(p).strip(' "\'') for p in re.split(r"\[\s*\.\.\.\s*\]|\(\s*\.\.\.\s*\)|\.\.\.|…", trecho)]
    return [p for p in partes if len(p) >= MIN_TRECHO]


def localizar(trecho: str, texto_limpo: str) -> dict | None:
    """Procura o trecho no texto (já limpo). Devolve modo, similaridade e a passagem com contexto."""
    partes = _partes(trecho)
    if not partes:
        return None
    alvo = texto_limpo.lower()
    if len(alvo) != len(texto_limpo):  # raro: caixa baixa mudou o tamanho; usa o mesmo texto para o contexto
        texto_limpo = alvo
    achados = []
    for parte in partes:
        agulha = parte.lower()
        inicio = alvo.find(agulha)
        if inicio >= 0:
            achados.append((100.0, inicio, inicio + len(agulha)))
            continue
        from rapidfuzz import fuzz

        alinhamento = fuzz.partial_ratio_alignment(agulha, alvo, score_cutoff=LIMIAR_APROXIMADO)
        if alinhamento is None:
            return None
        achados.append((alinhamento.score, alinhamento.dest_start, alinhamento.dest_end))
    similaridade = min(a[0] for a in achados)
    inicio, fim = min(a[1] for a in achados), max(a[2] for a in achados)
    if fim - inicio > 6 * JANELA:  # partes distantes: mostra só a primeira
        _, inicio, fim = achados[0]
    return {
        "modo": "literal" if similaridade == 100 else "aproximado",
        "similaridade": round(similaridade, 1),
        "passagem": texto_limpo[max(0, inicio - JANELA): fim + JANELA],
    }


class Corpus:
    """Textos dos documentos originais registrados no manifesto."""

    def __init__(self, conferir_originais: bool = True):
        self.docs = {r["doc_id"]: r for r in ler_manifesto() if r["situacao"] == "ok"}
        self.alterados: set[str] = set()
        if conferir_originais:
            for doc_id, reg in self.docs.items():
                original = caminhos.CORPUS / reg["origem"]
                if not original.is_file() or sha256_arquivo(original) != reg["sha256"]:
                    self.alterados.add(doc_id)
        self.texto = lru_cache(maxsize=None)(self._texto)

    def _texto(self, doc_id: str) -> str:
        return limpar((caminhos.RAIZ / self.docs[doc_id]["texto"]).read_text(encoding="utf-8"))

    def conferir(self, evidencia: dict) -> dict:
        """Procura o trecho no documento citado e, se não achar, nos demais documentos do corpus."""
        trecho = evidencia.get("trecho", "")
        citado = evidencia.get("doc_id", "")
        saida = {
            "trecho": trecho,
            "documento_citado": evidencia.get("documento", ""),
            "situacao": "nao_localizado",
            "documento_localizado": "",
            "modo": "",
            "similaridade": 0,
            "passagem": "",
        }
        if not _partes(trecho):
            saida["situacao"] = "trecho_curto_demais"
            return saida
        validos = [d for d in self.docs if d not in self.alterados]
        ordem = ([citado] if citado in validos else []) + [d for d in validos if d != citado]
        for doc_id in ordem:
            achado = localizar(trecho, self.texto(doc_id))
            if achado:
                saida.update(achado)
                saida["documento_localizado"] = self.docs[doc_id]["origem"]
                saida["situacao"] = "localizado" if doc_id == citado else "localizado_em_outro_documento"
                return saida
        if citado in self.alterados:
            saida["situacao"] = "original_ausente_ou_alterado"
        return saida


ESQUEMA_JUIZ = {
    "type": "object",
    "additionalProperties": False,
    "required": ["veredito", "justificativa", "afirmacoes_sem_respaldo"],
    "properties": {
        "veredito": {"type": "string", "enum": ["sustentada", "parcial", "nao_sustentada"]},
        "justificativa": {"type": "string"},
        "afirmacoes_sem_respaldo": {"type": "array", "items": {"type": "string"}},
    },
}

INSTRUCOES_JUIZ = (
    "Você audita uma resposta produzida a partir de documentos. Compare a resposta APENAS com as "
    "passagens fornecidas, que foram extraídas dos documentos originais; não use conhecimento externo. "
    "As passagens podem estar em outro idioma: a resposta pode parafrasear ou traduzir, mas o conteúdo "
    "precisa estar nelas.\n"
    "veredito = 'sustentada' se todas as afirmações relevantes da resposta têm respaldo nas passagens; "
    "'parcial' se a maior parte tem respaldo mas alguma afirmação relevante não tem; "
    "'nao_sustentada' se o conteúdo central não tem respaldo.\n"
    "Liste em afirmacoes_sem_respaldo cada afirmação da resposta que não encontrou apoio. "
    "Escreva a justificativa em português, em até três frases."
)


def julgar(pergunta: str, resposta: str, passagens: list[dict], api) -> dict:
    conteudo = {
        "pergunta": pergunta,
        "resposta_a_conferir": resposta,
        "passagens_dos_documentos_originais": [
            {"documento": p["documento_localizado"], "passagem": p["passagem"]} for p in passagens
        ],
    }
    saida = api.responses.create(
        model=os.environ.get("RAG_MODELO_JUIZ", "gpt-4o-mini"),
        instructions=INSTRUCOES_JUIZ,
        input=json.dumps(conteudo, ensure_ascii=False),
        temperature=0,
        text={"format": {"type": "json_schema", "name": "juizo", "schema": ESQUEMA_JUIZ, "strict": True}},
    )
    try:
        juizo = json.loads(saida.output_text)
        assert juizo["veredito"] in {"sustentada", "parcial", "nao_sustentada"}
        return juizo
    except Exception:
        return {"veredito": "indefinido", "justificativa": "O juiz não devolveu a estrutura esperada.",
                "afirmacoes_sem_respaldo": []}


def validar_item(item: dict, corpus: Corpus, api=None, usar_juiz: bool = True) -> dict:
    """Valida uma resposta. Status: VALIDADA, PARCIAL, NAO_VALIDADA ou SEM_RESPOSTA_NO_CORPUS."""
    conferidas = [corpus.conferir(ev) for ev in item.get("evidencias", [])]
    localizadas = [c for c in conferidas if c["situacao"].startswith("localizado")]
    resultado = {
        "id": item.get("id", ""),
        "pergunta": item.get("pergunta", ""),
        "resposta": item.get("resposta", ""),
        "trechos_citados": len(conferidas),
        "trechos_localizados": len(localizadas),
        "veredito_juiz": "",
        "justificativa": "",
        "afirmacoes_sem_respaldo": [],
        "evidencias": conferidas,
    }
    if not item.get("encontrou_resposta", True) and not conferidas:
        resultado["status"] = "SEM_RESPOSTA_NO_CORPUS"
        resultado["justificativa"] = "O RAG informou que o corpus não traz a informação; não há conteúdo a validar."
        return resultado
    if not localizadas:
        resultado["status"] = "NAO_VALIDADA"
        resultado["justificativa"] = "Nenhum trecho citado foi localizado nos documentos originais do corpus."
        return resultado
    if not usar_juiz:
        resultado["status"] = "VALIDADA" if len(localizadas) == len(conferidas) else "PARCIAL"
        resultado["justificativa"] = "Conferência apenas literal (juiz desligado)."
        return resultado

    juizo = julgar(item["pergunta"], item["resposta"], localizadas, api or cliente())
    resultado["veredito_juiz"] = juizo["veredito"]
    resultado["justificativa"] = juizo["justificativa"]
    resultado["afirmacoes_sem_respaldo"] = juizo["afirmacoes_sem_respaldo"]
    resultado["status"] = {"sustentada": "VALIDADA", "parcial": "PARCIAL"}.get(juizo["veredito"], "NAO_VALIDADA")
    return resultado


def rodadas() -> list[str]:
    if not caminhos.RESPOSTAS.exists():
        return []
    return sorted(p.stem for p in caminhos.RESPOSTAS.glob("*.json"))


def validar_rodada(rodada: str, avisar=print, api=None, usar_juiz: bool = True) -> list[dict]:
    """Valida todas as respostas de uma rodada e grava .json (detalhe) e .csv (resumo)."""
    dados = json.loads((caminhos.RESPOSTAS / f"{rodada}.json").read_text(encoding="utf-8"))
    corpus = Corpus()
    if corpus.alterados:
        avisar(f"Atenção: {len(corpus.alterados)} documento(s) original(is) mudaram ou sumiram desde a extração. "
               "Eles não contam como prova; refaça os passos 2 e 3.")
    if usar_juiz:
        api = api or cliente()
    resultados = []
    for n, item in enumerate(dados["itens"], start=1):
        r = validar_item(item, corpus, api=api, usar_juiz=usar_juiz)
        resultados.append(r)
        avisar(f"[{n}/{len(dados['itens'])}] {r['id']}: {r['status']} "
               f"({r['trechos_localizados']}/{r['trechos_citados']} trechos localizados)")

    caminhos.VALIDACAO.mkdir(parents=True, exist_ok=True)
    (caminhos.VALIDACAO / f"{rodada}.json").write_text(
        json.dumps({"rodada": rodada, "resultados": resultados}, ensure_ascii=False, indent=2), encoding="utf-8")
    colunas = ["id", "pergunta", "status", "trechos_citados", "trechos_localizados", "veredito_juiz", "justificativa"]
    with (caminhos.VALIDACAO / f"{rodada}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(resultados)
    return resultados
