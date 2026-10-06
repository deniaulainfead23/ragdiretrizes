"""Passo 3: enviar os textos extraídos para um Vector Store da OpenAI."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from . import caminhos
from .extracao import ler_manifesto


def cliente():
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(caminhos.RAIZ / ".env")
    chave = os.environ.get("OPENAI_API_KEY", "").strip()
    if not chave:
        raise RuntimeError("OPENAI_API_KEY não definida. Copie .env.example para .env e preencha a chave.")
    return OpenAI(api_key=chave)


def ler_indice() -> dict:
    if not caminhos.INDICE.exists():
        return {}
    try:
        return json.loads(caminhos.INDICE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _gravar_indice(indice: dict) -> None:
    indice["atualizado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    caminhos.INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")


def pendencias() -> tuple[list[dict], list[str]]:
    """Compara manifesto e índice: (documentos a enviar, doc_ids a retirar do índice)."""
    prontos = {r["doc_id"]: r for r in ler_manifesto() if r["situacao"] == "ok"}
    enviados = ler_indice().get("arquivos", {})
    enviar = [r for doc_id, r in prontos.items() if doc_id not in enviados]
    retirar = [doc_id for doc_id in enviados if doc_id not in prontos]
    return enviar, retirar


def indexar(avisar=print, api=None) -> dict:
    """Sincroniza o Vector Store com o manifesto: envia o que é novo, retira o que saiu do corpus."""
    enviar, retirar = pendencias()
    indice = ler_indice()
    api = api or cliente()

    if not indice.get("vector_store_id"):
        vs = api.vector_stores.create(name="ragclean-" + datetime.now().strftime("%Y%m%d-%H%M"))
        indice = {"vector_store_id": vs.id, "arquivos": {}}
        _gravar_indice(indice)
        avisar(f"Vector Store criado: {vs.id}")
    vs_id = indice["vector_store_id"]

    for doc_id in retirar:
        file_id = indice["arquivos"][doc_id]["file_id"]
        try:
            api.vector_stores.files.delete(file_id, vector_store_id=vs_id)
            api.files.delete(file_id)
        except Exception as exc:  # já removido do lado da OpenAI
            avisar(f"  aviso ao retirar {doc_id}: {type(exc).__name__}")
        del indice["arquivos"][doc_id]
        _gravar_indice(indice)
        avisar(f"Retirado do índice: {doc_id}")

    for n, reg in enumerate(enviar, start=1):
        conteudo = (caminhos.RAIZ / reg["texto"]).read_bytes()
        atributos = {"doc_id": reg["doc_id"], "origem": reg["origem"][:500]}
        if reg["pasta"]:
            atributos["pasta"] = reg["pasta"]
        enviado = api.vector_stores.files.upload_and_poll(
            vector_store_id=vs_id,
            file=(f"{reg['doc_id']}.txt", conteudo),
            attributes=atributos,
        )
        if enviado.status != "completed":
            avisar(f"[{n}/{len(enviar)}] FALHOU {reg['origem']}: {enviado.status}")
            continue
        indice["arquivos"][reg["doc_id"]] = {"file_id": enviado.id, "origem": reg["origem"]}
        _gravar_indice(indice)  # grava a cada arquivo: se cair no meio, continua de onde parou
        avisar(f"[{n}/{len(enviar)}] indexado: {reg['origem']}")

    return indice


def apagar_indice(avisar=print, api=None) -> None:
    """Apaga o Vector Store e os arquivos enviados à OpenAI."""
    indice = ler_indice()
    if indice.get("vector_store_id"):
        api = api or cliente()
        for info in indice.get("arquivos", {}).values():
            try:
                api.files.delete(info["file_id"])
            except Exception:
                pass
        try:
            api.vector_stores.delete(indice["vector_store_id"])
            avisar(f"Vector Store apagado: {indice['vector_store_id']}")
        except Exception as exc:
            avisar(f"Não foi possível apagar o Vector Store: {type(exc).__name__}")
    caminhos.INDICE.unlink(missing_ok=True)
