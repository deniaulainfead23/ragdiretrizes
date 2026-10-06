"""Comparação TF-IDF do corpus com uma fonte de referência definida pela pessoa.

A fonte de referência pode ser:
  - uma LISTA DE TERMOS (palavras ou expressões, com categoria opcional): mede onde e quanto
    cada termo aparece nos documentos; ou
  - um DOCUMENTO DE REFERÊNCIA (ex.: um framework): mede a proximidade de vocabulário entre
    ele e cada documento ou pasta do corpus.

Tudo roda na máquina, sem API. Usa os textos extraídos no passo 2.
"""
from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from . import caminhos, extracao
from .validacao import limpar

FORMATOS_LISTA = {".txt", ".csv"}
FORMATOS_DOCUMENTO = {".pdf", ".docx", ".txt", ".md", ".html", ".htm"}
RAIZ_DO_CORPUS = "(raiz)"
COLUNA_TERMO = {"termo", "termos", "term", "palavra", "palavras", "keyword", "keywords", "expressao", "expressão"}
COLUNA_CATEGORIA = {"categoria", "category", "area", "área", "eixo", "grupo", "dimensao", "dimensão"}


# ───────────────────────────── texto ─────────────────────────────

def _base(c: str) -> str:
    """Um caractere sem acento e em minúscula, mantendo o tamanho do texto (ç->c, É->e)."""
    for d in unicodedata.normalize("NFKD", c):
        if not unicodedata.combining(d):
            c = d
            break
    m = c.lower()
    return m if len(m) == 1 else c


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para 'educação' e 'educacao' contarem como a mesma palavra."""
    return "".join(_base(c) for c in texto)


def _numero(valor: float, casas: int = 3) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")  # vírgula decimal: abre certo no Excel em português


def _gravar_csv(caminho: Path, cabecalho: list[str], linhas: list[list]) -> None:
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)


# ───────────────────────────── corpus ─────────────────────────────

def carregar_grupos(por: str = "documento", excluir_sha: str = "") -> dict[str, list[dict]]:
    """Agrupa os documentos extraídos. por='documento' (um grupo por arquivo) ou 'pasta'."""
    grupos: dict[str, list[dict]] = defaultdict(list)
    for reg in extracao.ler_manifesto():
        if reg["situacao"] != "ok" or reg["sha256"] == excluir_sha:
            continue
        limpo = limpar((caminhos.RAIZ / reg["texto"]).read_text(encoding="utf-8"))
        doc = {"origem": reg["origem"], "limpo": limpo, "norm": normalizar(limpo)}
        grupos[reg["origem"] if por == "documento" else (reg["pasta"] or RAIZ_DO_CORPUS)].append(doc)
    return dict(sorted(grupos.items()))


# ──────────────────────── fonte: lista de termos ────────────────────────

def ler_termos(caminho: Path) -> list[dict]:
    """Lê uma lista de termos de .txt ou .csv. Formatos aceitos por linha: 'termo' ou 'categoria;termo'."""
    bruto = caminho.read_bytes()
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("latin-1")
    linhas = [l.strip() for l in texto.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not linhas:
        return []
    sep = ";" if any(";" in l for l in linhas) else ("\t" if any("\t" in l for l in linhas) else
                                                     ("," if caminho.suffix.lower() == ".csv" else None))
    partes = [[c.strip().strip('"') for c in (l.split(sep) if sep else [l])] for l in linhas]
    i_termo, i_cat = (1, 0) if max(len(p) for p in partes) > 1 else (0, None)
    cabecalho = [c.lower() for c in partes[0]]
    if any(c in COLUNA_TERMO for c in cabecalho):
        i_termo = next(i for i, c in enumerate(cabecalho) if c in COLUNA_TERMO)
        i_cat = next((i for i, c in enumerate(cabecalho) if c in COLUNA_CATEGORIA), None)
        partes = partes[1:]
    itens = []
    for p in partes:
        termo = p[i_termo] if len(p) > i_termo else (p[0] if len(p) == 1 else "")
        categoria = p[i_cat] if i_cat is not None and len(p) > i_cat and len(p) > 1 else ""
        itens.append({"categoria": categoria, "termo": termo})
    return conferir_termos(itens)


def termos_digitados(texto: str) -> list[dict]:
    """Termos separados por vírgula ou ponto e vírgula, digitados no menu."""
    return conferir_termos([{"categoria": "", "termo": t} for t in re.split(r"[;,\n]", texto)])


def conferir_termos(itens: list[dict]) -> list[dict]:
    """Tira vazios e repetidos (ignorando acento e maiúsculas)."""
    vistos, saida = set(), []
    for item in itens:
        termo = re.sub(r"\s+", " ", str(item.get("termo", ""))).strip()
        chave = (normalizar(item.get("categoria", "")), normalizar(termo))
        if len(termo.replace("*", "")) < 2 or chave in vistos:
            continue
        vistos.add(chave)
        saida.append({"categoria": str(item.get("categoria", "")).strip(), "termo": termo})
    return saida


def _padrao(termo: str) -> re.Pattern:
    """Termo -> busca por palavra inteira. Aceita expressão ('data literacy') e curinga ('algoritm*')."""
    corpo = re.escape(normalizar(termo)).replace(r"\*", r"\w*").replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){corpo}(?!\w)")


def comparar_termos(termos: list[dict], por: str = "documento", nome: str = "termos", avisar=print) -> Path:
    """Conta cada termo em cada grupo, calcula o TF-IDF e grava os resultados. Devolve a pasta de saída."""
    grupos = carregar_grupos(por)
    if not grupos:
        raise RuntimeError("Não há textos extraídos. Faça o passo 2 primeiro.")
    if not termos:
        raise RuntimeError("A lista de termos está vazia.")
    nomes = list(grupos)
    palavras = {g: sum(len(re.findall(r"\w+", d["norm"])) for d in docs) or 1 for g, docs in grupos.items()}
    contagem = [[0] * len(nomes) for _ in termos]
    trechos = []
    for i, item in enumerate(termos):
        padrao = _padrao(item["termo"])
        for j, g in enumerate(nomes):
            for doc in grupos[g]:
                achados = list(padrao.finditer(doc["norm"]))
                contagem[i][j] += len(achados)
                for m in achados[:2]:  # até dois trechos por termo e documento, para conferência
                    trecho = doc["limpo"][max(0, m.start() - 120): m.end() + 120]
                    trechos.append([g, doc["origem"], item["categoria"], item["termo"], "…" + trecho + "…"])
        avisar(f"[{i + 1}/{len(termos)}] {item['termo']}: {sum(contagem[i])} ocorrência(s) "
               f"em {sum(1 for c in contagem[i] if c)} de {len(nomes)}")

    n = len(nomes)
    por_10mil = [[c / palavras[g] * 1e4 for c, g in zip(linha, nomes)] for linha in contagem]
    idf = [math.log((1 + n) / (1 + sum(1 for c in linha if c))) + 1 for linha in contagem]
    tfidf = [[f * idf[i] for f in linha] for i, linha in enumerate(por_10mil)]

    saida = _pasta_de_saida(nome)
    rotulo = "documento" if por == "documento" else "pasta"
    ident = [[t["categoria"], t["termo"]] for t in termos]
    _gravar_csv(saida / "ocorrencias.csv", ["categoria", "termo", "total", f"{rotulo}s_com_o_termo"] + nomes,
                [ident[i] + [sum(l), sum(1 for c in l if c)] + l for i, l in enumerate(contagem)])
    _gravar_csv(saida / "frequencia_por_10mil_palavras.csv", ["categoria", "termo"] + nomes,
                [ident[i] + [_numero(v, 2) for v in l] for i, l in enumerate(por_10mil)])
    _gravar_csv(saida / "tfidf.csv", ["categoria", "termo", "idf"] + nomes,
                [ident[i] + [_numero(idf[i])] + [_numero(v) for v in l] for i, l in enumerate(tfidf)])
    cobertura = sorted(
        ([g, len(grupos[g]), palavras[g], sum(1 for l in contagem if l[j]), len(termos),
          _numero(100 * sum(1 for l in contagem if l[j]) / len(termos), 1), sum(l[j] for l in contagem)]
         for j, g in enumerate(nomes)), key=lambda l: -l[3])
    _gravar_csv(saida / "cobertura.csv",
                [rotulo, "documentos", "palavras", "termos_encontrados", "termos_da_lista", "cobertura_%",
                 "ocorrencias"], cobertura)
    _gravar_csv(saida / "trechos_para_conferencia.csv", [rotulo, "documento", "categoria", "termo", "trecho"], trechos)

    categorias = list(dict.fromkeys(t["categoria"] for t in termos if t["categoria"]))
    matriz_cat = []
    if categorias:
        for cat in categorias:
            idx = [i for i, t in enumerate(termos) if t["categoria"] == cat]
            matriz_cat.append([sum(por_10mil[i][j] for i in idx) for j in range(n)])
        _gravar_csv(saida / "por_categoria.csv",
                    ["categoria", "termos", "medida"] + nomes,
                    [linha for k, cat in enumerate(categorias) for linha in (
                        [cat, sum(1 for t in termos if t["categoria"] == cat), "ocorrências"]
                        + [sum(contagem[i][j] for i, t in enumerate(termos) if t["categoria"] == cat) for j in range(n)],
                        [cat, "", "por 10 mil palavras"] + [_numero(v, 2) for v in matriz_cat[k]])])

    if categorias:
        grafico = _mapa_de_calor(saida / "mapa_de_calor.png", categorias, nomes, matriz_cat,
                                 "Ocorrências por 10 mil palavras, por categoria")
    else:
        grafico = _mapa_de_calor(saida / "mapa_de_calor.png", [t["termo"] for t in termos][:40], nomes,
                                 por_10mil[:40], "Ocorrências por 10 mil palavras, por termo")
    sem_nada = [c[0] for c in cobertura if c[3] == 0]
    _resumo(saida, "lista de termos", nome, por, {
        "termos": len(termos), "categorias": len(categorias), f"{rotulo}s": n,
    }, [
        ("cobertura.csv", f"comece por aqui: quantos termos da lista cada {rotulo} contém"),
        ("ocorrencias.csv", f"quantas vezes cada termo aparece em cada {rotulo}"),
        ("frequencia_por_10mil_palavras.csv", "o mesmo, descontando o tamanho dos textos; use esta para comparar"),
        ("tfidf.csv", "frequência × raridade: destaca termos que distinguem um grupo dos outros"),
        ("por_categoria.csv" if categorias else "", "soma dos termos de cada categoria"),
        ("trechos_para_conferencia.csv", "onde o termo aparece no texto, para conferir se o sentido é o esperado"),
        ("mapa_de_calor.png" if grafico else "", "visão geral"),
    ], [
        "Maiores coberturas: " + "; ".join(f"{c[0]} ({c[3]}/{c[4]})" for c in cobertura[:5]),
        (f"Sem nenhum termo da lista ({len(sem_nada)}): " + "; ".join(sem_nada[:15])
         + ". Confira se estão em outro idioma." if sem_nada else "Todos os grupos têm ao menos um termo."),
    ], {"termos": termos})
    return saida


# ──────────────────── fonte: documento de referência ────────────────────

def _stopwords() -> list[str]:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

    palavras = set(ENGLISH_STOP_WORDS)
    if caminhos.STOPWORDS.exists():
        for linha in caminhos.STOPWORDS.read_text(encoding="utf-8").splitlines():
            if not linha.lstrip().startswith("#"):
                palavras |= {normalizar(p) for p in linha.split()}
    return sorted(palavras)


def comparar_documento(referencia: Path, por: str = "documento", avisar=print) -> Path:
    """Mede a proximidade de vocabulário (cosseno TF-IDF) entre a referência e cada grupo do corpus."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    texto_ref = limpar(extracao.extrair_texto(referencia))
    if len(texto_ref) < extracao.MIN_CARACTERES:
        raise RuntimeError(f"Não consegui extrair texto de {referencia.name} (PDF escaneado?).")
    sha_ref = extracao.sha256_arquivo(referencia)
    no_corpus = [r["origem"] for r in extracao.ler_manifesto() if r["sha256"] == sha_ref]
    grupos = carregar_grupos(por, excluir_sha=sha_ref)
    if not grupos:
        raise RuntimeError("Não há textos extraídos. Faça o passo 2 primeiro.")
    nomes = list(grupos)
    textos = [" ".join(d["norm"] for d in grupos[g]) for g in nomes]
    avisar(f"Calculando TF-IDF de {len(nomes)} grupo(s) contra {referencia.name}…")

    vetorizador = TfidfVectorizer(
        lowercase=False, token_pattern=r"(?u)\b[^\W\d_]{3,}\b", ngram_range=(1, 2),
        stop_words=_stopwords(), sublinear_tf=True, max_features=200000)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        matriz = vetorizador.fit_transform(textos + [normalizar(texto_ref)])
    vocabulario = vetorizador.get_feature_names_out()
    ref = matriz[len(nomes)]
    similaridade = (matriz[: len(nomes)] @ ref.T).toarray().ravel()
    pesos_ref = ref.toarray().ravel()

    linhas = []
    for j, g in enumerate(nomes):
        produto = matriz[j].multiply(ref).toarray().ravel()
        comuns = [vocabulario[k] for k in produto.argsort()[::-1][:15] if produto[k] > 0]
        linhas.append([g, len(grupos[g]), _numero(float(similaridade[j])), int((produto > 0).sum()),
                       ", ".join(comuns)])
    ordem = sorted(range(len(nomes)), key=lambda j: -similaridade[j])
    rotulo = "documento" if por == "documento" else "pasta"

    saida = _pasta_de_saida(referencia.stem)
    _gravar_csv(saida / "similaridade.csv",
                [rotulo, "documentos", "similaridade", "termos_em_comum", "principais_termos_em_comum"],
                [linhas[j] for j in ordem])
    presenca = (matriz[: len(nomes)] > 0).sum(axis=0).A1  # em quantos grupos cada termo aparece
    ordenados = [k for k in pesos_ref.argsort()[::-1] if pesos_ref[k] > 0]
    principais = [k for k in ordenados if presenca[k] > 0][:60]
    exclusivos = [k for k in ordenados if presenca[k] == 0][:40]
    densa = matriz[: len(nomes)][:, principais].toarray()
    _gravar_csv(saida / "termos_so_na_referencia.csv", ["termo", "peso_na_referencia"],
                [[vocabulario[k], _numero(float(pesos_ref[k]))] for k in exclusivos])
    _gravar_csv(saida / "termos_da_referencia.csv",
                ["termo", "peso_na_referencia", f"{rotulo}s_com_o_termo"] + nomes,
                [[vocabulario[k], _numero(float(pesos_ref[k])), int((densa[:, c] > 0).sum())]
                 + [_numero(float(v)) for v in densa[:, c]] for c, k in enumerate(principais)])
    grafico = _barras(saida / "similaridade.png", [nomes[j] for j in ordem], [float(similaridade[j]) for j in ordem],
                      f"Similaridade TF-IDF com {referencia.name}")
    sem_nada = [nomes[j] for j in ordem if similaridade[j] < 0.02]
    _resumo(saida, "documento de referência", referencia.name, por, {
        "grupos comparados": len(nomes), "termos no vocabulário": len(vocabulario),
    }, [
        ("similaridade.csv", f"comece por aqui: ranking de proximidade de cada {rotulo} com a referência "
                             "(0 = nenhum vocabulário em comum, 1 = idêntico) e os termos que explicam o valor"),
        ("termos_da_referencia.csv", f"os 60 termos mais fortes da referência que também aparecem no corpus, "
                                     f"com o peso em cada {rotulo}"),
        ("termos_so_na_referencia.csv", "os 40 termos mais fortes da referência que não aparecem em nenhum documento "
                                        "do corpus (lacunas de vocabulário, ou cabeçalhos repetidos da referência)"),
        ("similaridade.png" if grafico else "", "o mesmo ranking em gráfico"),
    ], [
        "Mais próximos: " + "; ".join(f"{nomes[j]} ({_numero(float(similaridade[j]), 2)})" for j in ordem[:5]),
        (f"Quase sem vocabulário em comum ({len(sem_nada)}): " + "; ".join(sem_nada[:15])
         + ". Em geral são documentos em idioma diferente do da referência." if sem_nada else ""),
        (f"A referência também está no corpus ({', '.join(no_corpus)}) e foi deixada fora da comparação."
         if no_corpus else ""),
    ], {"referencia": referencia.name, "sha256_referencia": sha_ref})
    return saida


# ───────────────────────────── saídas ─────────────────────────────

def _pasta_de_saida(nome: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", normalizar(nome)).strip("-")[:40] or "comparacao"
    base = caminhos.TFIDF / f"{datetime.now():%Y%m%d-%H%M%S}_{slug}"
    saida, n = base, 1
    while saida.exists():
        n += 1
        saida = base.with_name(f"{base.name}-{n}")
    saida.mkdir(parents=True)
    return saida


def _resumo(saida: Path, fonte: str, nome: str, por: str, numeros: dict, arquivos: list, achados: list,
            parametros: dict) -> None:
    linhas = [f"# Comparação TF-IDF — {nome}", "",
              f"- Data: {datetime.now():%d/%m/%Y %H:%M}",
              f"- Fonte de comparação: {fonte} (`{nome}`)",
              f"- Unidade comparada: {'cada documento' if por == 'documento' else 'cada pasta do corpus'}"]
    linhas += [f"- {k.capitalize()}: {v}" for k, v in numeros.items()]
    linhas += ["", "## Principais resultados", ""] + [f"- {a}" for a in achados if a]
    linhas += ["", "## Arquivos desta pasta", ""] + [f"- `{a}` — {d}" for a, d in arquivos if a]
    linhas += ["", "## Como ler", "",
               "- A comparação é lexical: conta palavras escritas, não significados. Um documento em outro",
               "  idioma, ou que trate do tema com outras palavras, aparece com valor baixo.",
               "- Valor alto indica vocabulário parecido, não que o documento cumpra ou adote a referência.",
               "- Textos longos têm mais ocorrências; para comparar, use as medidas relativas (por 10 mil",
               "  palavras, TF-IDF, similaridade), não a contagem bruta.",
               "- Os CSV usam ponto e vírgula e vírgula decimal (abrem direto no Excel em português).",
               "- Guia completo: COMO_COMPARAR_TFIDF.md, na raiz do projeto."]
    (saida / "LEIA-ME.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (saida / "parametros.json").write_text(json.dumps(
        {"fonte": fonte, "nome": nome, "por": por, **numeros, **parametros}, ensure_ascii=False, indent=2),
        encoding="utf-8")


def _figura():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _curto(texto: str, n: int = 55) -> str:
    return texto if len(texto) <= n else "…" + texto[-(n - 1):]


def _barras(caminho: Path, nomes: list[str], valores: list[float], titulo: str) -> bool:
    try:
        plt = _figura()
        nomes, valores = nomes[:40][::-1], valores[:40][::-1]
        fig, ax = plt.subplots(figsize=(9, max(3, 0.32 * len(nomes) + 1.2)))
        ax.barh([_curto(n) for n in nomes], valores, color="#3b6ea5")
        ax.set_xlabel("similaridade (cosseno TF-IDF)")
        ax.set_title(titulo, fontsize=11)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        fig.tight_layout()
        fig.savefig(caminho, dpi=150)
        plt.close(fig)
        return True
    except Exception:
        return False


def _mapa_de_calor(caminho: Path, linhas: list[str], colunas: list[str], valores: list[list[float]], titulo: str) -> bool:
    try:
        plt = _figura()
        colunas, valores = colunas[:45], [v[:45] for v in valores]
        fig, ax = plt.subplots(figsize=(max(6, 0.42 * len(colunas) + 4), max(3, 0.4 * len(linhas) + 2.2)))
        imagem = ax.imshow(valores, aspect="auto", cmap="Blues")
        ax.set_xticks(range(len(colunas)), [_curto(c, 28) for c in colunas], rotation=60, ha="right", fontsize=8)
        ax.set_yticks(range(len(linhas)), [_curto(l, 45) for l in linhas], fontsize=8)
        ax.set_title(titulo, fontsize=11)
        fig.colorbar(imagem, ax=ax, shrink=0.8)
        fig.tight_layout()
        fig.savefig(caminho, dpi=150)
        plt.close(fig)
        return True
    except Exception:
        return False


# ───────────────────── arquivos disponíveis para o menu ─────────────────────

def arquivos_de_referencia(tipo: str) -> list[Path]:
    """tipo='lista' (.txt/.csv) ou 'documento' (.pdf, .docx, .txt, .md, .html) em dados_brutos/referencias."""
    formatos = FORMATOS_LISTA if tipo == "lista" else FORMATOS_DOCUMENTO
    pasta = caminhos.REFERENCIAS
    if not pasta.exists():
        return []
    return sorted(a for a in pasta.iterdir()
                  if a.is_file() and a.suffix.lower() in formatos and a.name.lower() != "readme.md")


def comparacoes() -> list[str]:
    return sorted(p.name for p in caminhos.TFIDF.iterdir() if p.is_dir()) if caminhos.TFIDF.exists() else []
