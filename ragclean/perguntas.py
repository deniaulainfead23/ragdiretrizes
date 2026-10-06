"""Catálogo de perguntas: ler, importar de arquivo (CSV, XLSX, YAML, TXT) e gravar."""
from __future__ import annotations

import csv
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml

from . import caminhos

FORMATOS = {".csv", ".xlsx", ".yaml", ".yml", ".txt"}
MODELO = "modelo_perguntas.csv"
APELIDOS = {
    "id": {"id", "question_id", "codigo", "código", "n", "nº", "numero", "número"},
    "titulo": {"titulo", "título", "title", "tema"},
    "pergunta": {"pergunta", "question_text", "question", "texto", "questao", "questão"},
}
CABECALHO = (
    "# Catálogo de perguntas do RagClean (usado no passo 4).\n"
    "# Cada pergunta tem: id (único), titulo (curto) e pergunta (o texto enviado ao RAG).\n"
    "# Pode editar aqui à mão ou importar um arquivo pelo menu (opção 6).\n"
    "# Como escrever boas perguntas: veja COMO_FAZER_PERGUNTAS.md ou a opção 'a' do menu.\n"
)


def carregar() -> list[dict]:
    if not caminhos.PERGUNTAS.exists():
        return []
    dados = yaml.safe_load(caminhos.PERGUNTAS.read_text(encoding="utf-8")) or {}
    return [_limpa(p) for p in dados.get("perguntas", [])]


def gravar(perguntas: list[dict]) -> None:
    """Grava o catálogo, guardando antes uma cópia do anterior em dados_intermediarios."""
    if caminhos.PERGUNTAS.exists():
        copia = caminhos.INTERMEDIARIOS / "perguntas_anteriores"
        copia.mkdir(parents=True, exist_ok=True)
        shutil.copy(caminhos.PERGUNTAS, copia / f"perguntas_{datetime.now():%Y%m%d-%H%M%S}.yaml")
    corpo = yaml.safe_dump({"perguntas": perguntas}, allow_unicode=True, sort_keys=False, width=1000)
    caminhos.PERGUNTAS.write_text(CABECALHO + corpo, encoding="utf-8")


def _limpa(p: dict) -> dict:
    junta = lambda v: re.sub(r"\s+", " ", str(v if v is not None else "")).strip()
    return {"id": junta(p.get("id")), "titulo": junta(p.get("titulo")), "pergunta": junta(p.get("pergunta"))}


def _mapear(linha: dict) -> dict:
    """Aceita nomes de coluna em português ou inglês (id/question_id, titulo/title, ...)."""
    saida = {}
    for chave, valor in linha.items():
        nome = str(chave or "").strip().lower().lstrip("﻿")
        for campo, nomes in APELIDOS.items():
            if nome in nomes:
                saida[campo] = valor
    return saida


def arquivos_para_importar() -> list[Path]:
    pasta = caminhos.PERGUNTAS_ENTRADA
    if not pasta.exists():
        return []
    return sorted(a for a in pasta.iterdir()
                  if a.is_file() and a.suffix.lower() in FORMATOS and a.name != MODELO)


def ler_arquivo(caminho: Path) -> list[dict]:
    """Lê perguntas de um arquivo. Devolve dicionários com id (pode vir vazio), titulo e pergunta."""
    ext = caminho.suffix.lower()
    if ext == ".txt":  # uma pergunta por linha; linhas vazias e iniciadas com # são ignoradas
        linhas = caminho.read_text(encoding="utf-8-sig").splitlines()
        return [_limpa({"pergunta": l}) for l in linhas if l.strip() and not l.lstrip().startswith("#")]
    if ext in {".yaml", ".yml"}:
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8-sig")) or {}
        itens = dados.get("perguntas") or dados.get("questions") or [] if isinstance(dados, dict) else dados
        return [_limpa(_mapear(i)) for i in itens if isinstance(i, dict)]
    if ext == ".xlsx":
        import openpyxl

        planilha = openpyxl.load_workbook(caminho, read_only=True, data_only=True).active
        linhas = [list(l) for l in planilha.iter_rows(values_only=True) if any(c not in (None, "") for c in l)]
        if not linhas:
            return []
        return [_limpa(_mapear(dict(zip(linhas[0], l)))) for l in linhas[1:]]
    if ext == ".csv":
        bruto = caminho.read_bytes()
        try:
            texto = bruto.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = bruto.decode("latin-1")  # CSV salvo pelo Excel em português
        primeira = texto.splitlines()[0] if texto.strip() else ""
        separador = ";" if primeira.count(";") > primeira.count(",") else ","
        return [_limpa(_mapear(l)) for l in csv.DictReader(texto.splitlines(), delimiter=separador)]
    raise ValueError(f"Formato não aceito: {ext}. Use CSV, XLSX, YAML ou TXT.")


def conferir(novas: list[dict], catalogo: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """Confere as perguntas lidas. Devolve (perguntas prontas, erros, avisos).

    Pergunta sem id recebe o próximo código livre (P01, P02, ...). Erros impedem a importação.
    """
    erros, avisos, prontas = [], [], []
    usados = {p["id"] for p in catalogo} | {p["id"] for p in novas if p["id"]}
    texto_do_catalogo = {p["pergunta"].lower(): p["id"] for p in catalogo}
    vistos_id, vistos_texto, contador = set(), {}, 0
    for n, p in enumerate(novas, start=1):
        if not p["pergunta"]:
            if p["id"] or p["titulo"]:
                erros.append(f"Linha {n}: sem texto na coluna 'pergunta'.")
            continue
        if not p["id"]:
            igual = texto_do_catalogo.get(p["pergunta"].lower())
            if igual:  # mesma pergunta já existe: mantém o id em vez de duplicar
                p["id"] = igual
            else:
                while True:
                    contador += 1
                    if f"P{contador:02d}" not in usados:
                        break
                p["id"] = f"P{contador:02d}"
                usados.add(p["id"])
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,20}", p["id"]):
            erros.append(f"Linha {n}: id '{p['id']}' inválido (use letras, números, - ou _, sem espaços).")
        if p["id"] in vistos_id:
            erros.append(f"Linha {n}: id '{p['id']}' repetido no arquivo.")
        vistos_id.add(p["id"])
        if len(p["pergunta"]) < 15:
            erros.append(f"Linha {n} ({p['id']}): pergunta curta demais para o RAG entender.")
        if p["pergunta"].lower() in vistos_texto:
            avisos.append(f"{p['id']}: mesmo texto de {vistos_texto[p['pergunta'].lower()]}.")
        vistos_texto[p["pergunta"].lower()] = p["id"]
        if re.search(r"\bp[áa]gina", p["pergunta"], re.IGNORECASE):
            avisos.append(f"{p['id']}: pede 'página'. O RagClean não usa página; peça documento e trecho.")
        if len(p["pergunta"]) > 600:
            avisos.append(f"{p['id']}: pergunta muito longa; costuma funcionar melhor dividida em duas.")
        if not p["titulo"]:
            p["titulo"] = p["pergunta"][:60].rstrip(" ?.,;:") + ("…" if len(p["pergunta"]) > 60 else "")
        prontas.append(p)
    if not prontas and not erros:
        erros.append("Nenhuma pergunta encontrada. O arquivo precisa de uma coluna chamada 'pergunta'.")
    return prontas, erros, avisos


def comparar(novas: list[dict], catalogo: list[dict], substituir: bool) -> dict:
    """Mostra o efeito da importação. `substituir` troca o catálogo inteiro; senão, junta."""
    atual = {p["id"]: p for p in catalogo}
    ids_novos = {p["id"] for p in novas}
    resultado = {
        "novas": [p for p in novas if p["id"] not in atual],
        "alteradas": [p for p in novas if p["id"] in atual and p["pergunta"] != atual[p["id"]]["pergunta"]],
        "iguais": [p for p in novas if p["id"] in atual and p["pergunta"] == atual[p["id"]]["pergunta"]],
        "removidas": [p for p in catalogo if p["id"] not in ids_novos] if substituir else [],
    }
    if substituir:
        resultado["catalogo"] = list(novas)
    else:
        por_id = {p["id"]: p for p in novas}
        resultado["catalogo"] = [por_id.pop(p["id"], p) for p in catalogo] + list(por_id.values())
    return resultado


def texto_da_ajuda() -> str:
    return caminhos.AJUDA_PERGUNTAS.read_text(encoding="utf-8")
