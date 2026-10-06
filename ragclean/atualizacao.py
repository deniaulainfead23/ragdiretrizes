"""Atualizar tudo: refaz só o que ficou desatualizado depois de mudar o corpus ou as perguntas."""
from __future__ import annotations

import json

from . import caminhos, consulta, extracao, indexacao, perguntas, validacao


def perguntas_pendentes(pasta: str = "") -> list[dict]:
    """Perguntas do catálogo sem resposta atual.

    Uma resposta é atual quando foi dada para o mesmo id e o mesmo texto, na mesma pasta,
    com o índice como está agora. Mudou o texto ou mudou o corpus: a pergunta volta a ficar pendente.
    """
    atual = indexacao.assinatura()
    respondidas = set()
    for rodada in validacao.rodadas():
        dados = json.loads((caminhos.RESPOSTAS / f"{rodada}.json").read_text(encoding="utf-8"))
        if dados.get("indice") != atual or dados.get("pasta", "") != pasta:
            continue
        respondidas |= {(i["id"], i["pergunta"]) for i in dados.get("itens", [])}
    return [p for p in perguntas.carregar() if (p["id"], p["pergunta"]) not in respondidas]


def rodadas_sem_validacao() -> list[str]:
    return [r for r in validacao.rodadas() if not (caminhos.VALIDACAO / f"{r}.json").exists()]


def plano(pasta: str = "") -> dict:
    """O que precisa ser refeito agora. Não altera nada."""
    arquivos, _ = extracao.listar_corpus()
    registrados = {r["origem"]: r["sha256"] for r in extracao.ler_manifesto()}
    no_corpus = {a.relative_to(caminhos.CORPUS).as_posix(): a for a in arquivos}
    mudou = set(no_corpus) != set(registrados) or any(
        extracao.sha256_arquivo(a) != registrados[origem] for origem, a in no_corpus.items())
    enviar, retirar = indexacao.pendencias()
    indice_muda = mudou or bool(enviar or retirar)
    catalogo = perguntas.carregar()
    return {
        "extrair": mudou,
        "indexar": indice_muda,
        "enviar": len(enviar),
        "retirar": len(retirar),
        # se o índice vai mudar, todas as respostas antigas deixam de valer
        "perguntas": catalogo if indice_muda else perguntas_pendentes(pasta),
        "validar": rodadas_sem_validacao(),
    }


def atualizar(pasta: str = "", avisar=print, api=None, api_juiz=None) -> dict:
    """Executa o plano na ordem: extrair, indexar, perguntar o que falta, validar o que falta."""
    feito = {"extraidos": 0, "rodada": "", "validadas": []}
    p = plano(pasta)
    if p["extrair"]:
        avisar("\n> Extraindo texto dos documentos novos ou alterados")
        feito["extraidos"] = len([r for r in extracao.extrair_corpus(avisar=avisar) if r["situacao"] == "ok"])
    enviar, retirar = indexacao.pendencias()
    if enviar or retirar:
        avisar("\n> Atualizando o índice")
        indexacao.indexar(avisar=avisar, api=api)
    pendentes = perguntas_pendentes(pasta)
    if pendentes:
        avisar(f"\n> Perguntando ao RAG ({len(pendentes)} pergunta(s))")
        feito["rodada"] = consulta.rodar(pendentes, pasta=pasta, avisar=avisar, api=api)
    for rodada in rodadas_sem_validacao():
        avisar(f"\n> Validando a rodada {rodada}")
        validacao.validar_rodada(rodada, avisar=avisar, api=api_juiz or api)
        feito["validadas"].append(rodada)
    return feito
