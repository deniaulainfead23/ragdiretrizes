"""Menu de passos do RagClean. Cada passo explica o que faz, pede confirmação e indica o próximo."""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from collections import Counter

from . import atualizacao, caminhos, consulta, extracao, indexacao, perguntas, validacao

LINHA = "─" * 72


def _rel(caminho) -> str:
    return caminho.relative_to(caminhos.RAIZ).as_posix()


def _confirmar(texto: str = "Executar agora?") -> bool:
    return input(f"\n{texto} [s/N] ").strip().lower() in {"s", "sim", "y"}


def _escolher(titulo: str, opcoes: list[str], permitir_vazio: str = "") -> str:
    print(f"\n{titulo}")
    for n, opcao in enumerate(opcoes, start=1):
        print(f"  {n}. {opcao}")
    dica = f" (Enter = {permitir_vazio})" if permitir_vazio else ""
    while True:
        escolha = input(f"Número{dica}: ").strip()
        if not escolha and permitir_vazio:
            return ""
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            return opcoes[int(escolha) - 1]
        print("Opção inválida.")


# ───────────────────────── situação de cada passo ─────────────────────────

def situacao() -> dict[int, tuple[bool, str]]:
    """Para cada passo: (concluído?, resumo em uma linha)."""
    arquivos, _ = extracao.listar_corpus()
    manifesto = extracao.ler_manifesto()
    prontos = [r for r in manifesto if r["situacao"] == "ok"]
    indice = indexacao.ler_indice()
    enviar, retirar = indexacao.pendencias() if manifesto else ([], [])
    rodadas = validacao.rodadas()
    validadas = [r for r in rodadas if (caminhos.VALIDACAO / f"{r}.json").exists()]

    dotenv_ok = False
    try:
        from dotenv import load_dotenv

        load_dotenv(caminhos.RAIZ / ".env")
        dotenv_ok = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    except ImportError:
        pass
    no_manifesto = {r["origem"] for r in manifesto}
    no_corpus = {a.relative_to(caminhos.CORPUS).as_posix() for a in arquivos}
    extraido = bool(manifesto) and no_corpus <= no_manifesto and no_manifesto <= no_corpus

    return {
        0: (dotenv_ok, "chave da OpenAI encontrada" if dotenv_ok else "falta a OPENAI_API_KEY no arquivo .env"),
        1: (bool(arquivos), f"{len(arquivos)} documento(s) em {_rel(caminhos.CORPUS)}"),
        2: (extraido, f"{len(prontos)} texto(s) extraído(s)" + ("" if extraido or not manifesto else " — corpus mudou, refazer")
            if manifesto else "ainda não executado"),
        3: (bool(indice.get("arquivos")) and not enviar and not retirar,
            f"{len(indice.get('arquivos', {}))} documento(s) no índice"
            + (f" — {len(enviar)} a enviar, {len(retirar)} a retirar" if enviar or retirar else "")
            if indice.get("vector_store_id") else "ainda não executado"),
        4: (bool(rodadas), f"{len(rodadas)} rodada(s) de respostas" if rodadas else "nenhuma pergunta feita"),
        5: (bool(rodadas) and len(validadas) == len(rodadas),
            f"{len(validadas)} de {len(rodadas)} rodada(s) validadas" if rodadas else "nada a validar"),
    }


PASSOS = {
    0: "Preparar o ambiente",
    1: "Conferir o corpus",
    2: "Extrair o texto dos documentos",
    3: "Indexar no Vector Store",
    4: "Perguntar ao RAG",
    5: "Validar as respostas",
}


def proximo(sit: dict) -> int | None:
    return next((n for n in PASSOS if not sit[n][0]), None)


# ───────────────────────────────── passos ─────────────────────────────────

def passo_0() -> None:
    print("O que este passo faz: confere se as bibliotecas estão instaladas e se a chave da OpenAI")
    print("está no arquivo .env. Não envia nada para a internet.\n")
    faltando = [nome for nome, modulo in [
        ("openai", "openai"), ("python-dotenv", "dotenv"), ("PyYAML", "yaml"), ("pymupdf", "pymupdf"),
        ("pdfplumber", "pdfplumber"), ("rapidfuzz", "rapidfuzz"), ("python-docx", "docx"),
    ] if importlib.util.find_spec(modulo) is None]
    if faltando:
        print("Bibliotecas faltando:", ", ".join(faltando))
        print("  Instale com:  pip install -r requirements.txt")
    else:
        print("Bibliotecas: todas instaladas.")
    env = caminhos.RAIZ / ".env"
    if not env.exists():
        shutil.copy(caminhos.RAIZ / ".env.example", env)
        print("Criei o arquivo .env a partir do modelo.")
    if situacao()[0][0]:
        print("Chave da OpenAI: encontrada.")
    else:
        print("Chave da OpenAI: abra o arquivo .env e preencha a linha OPENAI_API_KEY=")
    for pasta in (caminhos.CORPUS, caminhos.INTERMEDIARIOS, caminhos.DERIVADOS):
        pasta.mkdir(parents=True, exist_ok=True)


def passo_1() -> None:
    print("O que este passo faz: lista o que está em dados_brutos/corpus. Só leitura, nada é alterado.")
    print("Você pode colocar os documentos em qualquer ordem e em quaisquer subpastas.\n")
    arquivos, ignorados = extracao.listar_corpus()
    if not arquivos:
        print(f"O corpus está vazio. Copie seus documentos para {_rel(caminhos.CORPUS)}/ e volte aqui.")
        return
    por_tipo = Counter(a.suffix.lower() for a in arquivos)
    por_pasta = Counter((a.relative_to(caminhos.CORPUS).parts[0] if len(a.relative_to(caminhos.CORPUS).parts) > 1
                         else "(raiz)") for a in arquivos)
    tamanho = sum(a.stat().st_size for a in arquivos) / 1e6
    print(f"{len(arquivos)} documento(s), {tamanho:.1f} MB")
    print("Por tipo:  " + ", ".join(f"{t} {n}" for t, n in sorted(por_tipo.items())))
    print("Por pasta:")
    for pasta, n in sorted(por_pasta.items()):
        print(f"  {pasta}: {n}")
    if ignorados:
        print(f"\n{len(ignorados)} arquivo(s) em formato não lido serão ignorados:")
        for a in ignorados[:10]:
            print("  " + a.relative_to(caminhos.CORPUS).as_posix())


def passo_2() -> None:
    print("O que este passo faz: lê cada documento do corpus e grava o texto em")
    print(f"{_rel(caminhos.TEXTOS)}/, com um registro por documento em {_rel(caminhos.MANIFESTO)}.")
    print("Roda na sua máquina, sem custo. Documentos já extraídos e não alterados são reaproveitados.")
    if not _confirmar():
        return
    registros = extracao.extrair_corpus()
    ok = [r for r in registros if r["situacao"] == "ok"]
    problema = [r for r in registros if r["situacao"] not in {"ok", "duplicado"}]
    print(f"\n{len(ok)} documento(s) com texto extraído.")
    if problema:
        print(f"{len(problema)} documento(s) sem texto aproveitável (ficam FORA do RAG):")
        for r in problema:
            print(f"  {r['origem']} — {r['situacao']}")
        print("Em geral são PDFs escaneados (imagem). Passe OCR neles e substitua o arquivo no corpus.")


def passo_3() -> None:
    enviar, retirar = indexacao.pendencias()
    indice = indexacao.ler_indice()
    print("O que este passo faz: envia os textos extraídos para um Vector Store da OpenAI, que")
    print("divide em trechos e cria os embeddings. É o único passo de indexação e é cobrado pela API.")
    print("Só o que é novo é enviado; o que saiu do corpus é retirado do índice.\n")
    print(f"Vector Store: {indice.get('vector_store_id') or '(será criado)'}")
    print(f"A enviar: {len(enviar)}   A retirar: {len(retirar)}   Já no índice: {len(indice.get('arquivos', {})) - len(retirar)}")
    if not enviar and not retirar:
        print("\nO índice já está em dia com o corpus.")
        return
    if not _confirmar():
        return
    indice = indexacao.indexar()
    print(f"\nÍndice com {len(indice['arquivos'])} documento(s). Registro em {_rel(caminhos.INDICE)}.")


def passo_4() -> None:
    print("O que este passo faz: envia perguntas ao RAG. Cada resposta volta com trechos copiados")
    print(f"dos documentos, e a rodada é gravada em {_rel(caminhos.RESPOSTAS)}/. Cobrado pela API.")
    catalogo = consulta.carregar_perguntas()
    modo = _escolher("Como quer perguntar?", [
        "Digitar uma pergunta",
        f"Rodar o catálogo inteiro ({len(catalogo)} perguntas de ragclean/perguntas.yaml)",
        "Escolher uma pergunta do catálogo",
    ])
    if modo.startswith("Digitar"):
        texto = input("\nPergunta: ").strip()
        if not texto:
            return
        perguntas = [{"id": "LIVRE", "titulo": "", "pergunta": texto}]
    elif modo.startswith("Rodar"):
        perguntas = catalogo
    else:
        rotulo = _escolher("Qual pergunta?", [f"{p['id']} — {p['titulo']}" for p in catalogo])
        perguntas = [p for p in catalogo if rotulo.startswith(p["id"] + " ")]

    pasta = ""
    pastas = consulta.pastas_do_corpus()
    if pastas:
        pasta = _escolher("Restringir a busca a uma pasta do corpus?", pastas, permitir_vazio="corpus inteiro")
    rodada = consulta.rodar(perguntas, pasta=pasta)
    arquivo = caminhos.RESPOSTAS / f"{rodada}.json"
    if not arquivo.exists():
        print("\nNenhuma resposta foi gravada.")
        return
    if len(perguntas) == 1:
        import json

        item = json.loads(arquivo.read_text(encoding="utf-8"))["itens"][0]
        print(f"\n{LINHA}\n{item['resposta']}\n")
        for n, ev in enumerate(item["evidencias"], start=1):
            print(f"  [{n}] {ev['documento']}\n      \"{ev['trecho'][:300]}\"")
    print(f"\nRodada gravada em {_rel(arquivo)}")


def passo_5() -> None:
    print("O que este passo faz: confere se o conteúdo de cada resposta tem respaldo nos documentos")
    print("originais do corpus. NÃO usa número de página.")
    print("  1) procura cada trecho citado no texto do documento original (tolerando quebras de linha);")
    print("  2) um juiz (LLM) confere se a resposta é sustentada pelas passagens localizadas.")
    print("VALIDADA = há trecho localizado e a resposta é sustentada. A etapa 2 é cobrada pela API.")
    todas = validacao.rodadas()
    if not todas:
        print("\nAinda não há respostas. Faça o passo 4 primeiro.")
        return
    pendentes = [r for r in todas if not (caminhos.VALIDACAO / f"{r}.json").exists()]
    rodada = _escolher("Qual rodada validar?", list(reversed(todas)),
                       permitir_vazio=f"a mais recente{' pendente' if pendentes else ''}")
    rodada = rodada or (pendentes or todas)[-1]
    resultados = validacao.validar_rodada(rodada)
    contagem = Counter(r["status"] for r in resultados)
    print(f"\n{LINHA}\nRodada {rodada}: " + ", ".join(f"{n} {s}" for s, n in contagem.most_common()))
    for r in resultados:
        if r["status"] in {"PARCIAL", "NAO_VALIDADA"}:
            print(f"  {r['id']} {r['status']}: {r['justificativa']}")
    print(f"\nResumo:  {_rel(caminhos.VALIDACAO / (rodada + '.csv'))}")
    print(f"Detalhe: {_rel(caminhos.VALIDACAO / (rodada + '.json'))}")


def catalogo_de_perguntas() -> None:
    catalogo = perguntas.carregar()
    print(f"O catálogo tem {len(catalogo)} pergunta(s), em {_rel(caminhos.PERGUNTAS)}.")
    acao = _escolher("O que quer fazer?", [
        "Ver as perguntas do catálogo",
        f"Importar perguntas de um arquivo em {_rel(caminhos.PERGUNTAS_ENTRADA)}/",
        "Remover uma pergunta",
    ])
    if acao.startswith("Ver"):
        for p in catalogo:
            print(f"\n  {p['id']} — {p['titulo']}\n     {p['pergunta']}")
        return
    if acao.startswith("Remover"):
        rotulo = _escolher("Qual pergunta remover?", [f"{p['id']} — {p['titulo']}" for p in catalogo])
        if _confirmar(f"Remover {rotulo}?"):
            perguntas.gravar([p for p in catalogo if not rotulo.startswith(p["id"] + " ")])
            print("Removida. As respostas antigas continuam guardadas como histórico.")
        return

    print("\nO que isto faz: lê um arquivo de perguntas (CSV, XLSX, TXT ou YAML), confere e mostra o")
    print("que muda no catálogo. Nada é gravado sem a sua confirmação e nada é enviado à internet.")
    caminhos.PERGUNTAS_ENTRADA.mkdir(parents=True, exist_ok=True)
    arquivos = perguntas.arquivos_para_importar()
    if not arquivos:
        print(f"\nNão há arquivo para importar. Salve o seu em {_rel(caminhos.PERGUNTAS_ENTRADA)}/")
        print(f"(use {perguntas.MODELO} como modelo) e volte aqui. Ajuda: opção 'a' do menu.")
        return
    nome = _escolher("Qual arquivo importar?", [a.name for a in arquivos])
    lidas = perguntas.ler_arquivo(caminhos.PERGUNTAS_ENTRADA / nome)
    prontas, erros, avisos = perguntas.conferir(lidas, catalogo)
    for aviso in avisos:
        print("  aviso: " + aviso)
    if erros:
        print("\nO arquivo tem problemas e não foi importado:")
        for erro in erros:
            print("  " + erro)
        return
    modo = _escolher("Como importar?", [
        "Juntar: acrescenta as novas e atualiza as de mesmo id (as demais ficam)",
        "Substituir: o catálogo passa a ser só o que está no arquivo",
    ])
    efeito = perguntas.comparar(prontas, catalogo, substituir=modo.startswith("Substituir"))
    print()
    for rotulo in ("novas", "alteradas", "removidas"):
        for p in efeito[rotulo]:
            print(f"  {rotulo[:-1].upper():<9} {p['id']}  {p['pergunta'][:80]}")
    print(f"\n{len(efeito['novas'])} nova(s), {len(efeito['alteradas'])} alterada(s), "
          f"{len(efeito['iguais'])} igual(is), {len(efeito['removidas'])} removida(s). "
          f"Catálogo ficará com {len(efeito['catalogo'])} pergunta(s).")
    if not (efeito["novas"] or efeito["alteradas"] or efeito["removidas"]):
        print("Nada a mudar.")
        return
    if _confirmar("Gravar o catálogo?"):
        perguntas.gravar(efeito["catalogo"])
        print("Catálogo gravado. Use a opção 7 (Atualizar tudo) para responder e validar o que mudou.")


def atualizar_tudo() -> None:
    print("O que isto faz: confere o corpus e o catálogo de perguntas e refaz só o que ficou")
    print("desatualizado: extração, índice, respostas e validação, nessa ordem.")
    sit = situacao()
    if not sit[0][0]:
        print("\nAntes falta concluir o passo 0 (chave da OpenAI).")
        return
    pasta = ""
    pastas = consulta.pastas_do_corpus()
    if pastas:
        pasta = _escolher("As perguntas valem para qual pasta do corpus?", pastas, permitir_vazio="corpus inteiro")
    p = atualizacao.plano(pasta)
    print("\nPlano:")
    print("  Extração:  " + ("refazer para os documentos novos ou alterados" if p["extrair"] else "em dia"))
    print("  Índice:    " + ("atualizar (cobrado pela API)" if p["indexar"] else "em dia"))
    if p["indexar"] and p["perguntas"]:
        print(f"  Perguntas: todas as {len(p['perguntas'])} serão respondidas de novo, porque o corpus mudou")
    else:
        print(f"  Perguntas: {len(p['perguntas'])} nova(s) ou alterada(s) a responder" if p["perguntas"]
              else "  Perguntas: em dia")
        for q in p["perguntas"]:
            print(f"               {q['id']}  {q['pergunta'][:70]}")
    print(f"  Validação: {len(p['validar'])} rodada(s) pendente(s)" + (" + a nova" if p["perguntas"] else ""))
    if not (p["extrair"] or p["indexar"] or p["perguntas"] or p["validar"]):
        print("\nEstá tudo em dia. Nada a fazer.")
        return
    if not _confirmar():
        return
    feito = atualizacao.atualizar(pasta)
    print(f"\n{LINHA}\nAtualização concluída.")
    for rodada in feito["validadas"]:
        print(f"  Validação: {_rel(caminhos.VALIDACAO / (rodada + '.csv'))}")


def ajuda_perguntas() -> None:
    print(perguntas.texto_da_ajuda())
    print(f"(Este texto está em {_rel(caminhos.AJUDA_PERGUNTAS)}; no VS Code, abra com Ctrl+Shift+V.)")


def recomecar() -> None:
    print("O que isto faz: apaga o Vector Store na OpenAI e tudo em dados_intermediarios e")
    print("dados_derivados. Os documentos originais em dados_brutos NÃO são tocados.")
    if not _confirmar("Apagar e recomeçar do zero?"):
        return
    try:
        indexacao.apagar_indice()
    except Exception as exc:
        print(f"Não consegui apagar o Vector Store ({exc}). Apagando só os arquivos locais.")
    for pasta in (caminhos.INTERMEDIARIOS, caminhos.DERIVADOS):
        for item in pasta.iterdir():
            if item.name == "README.md":
                continue
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    print("Pronto. Comece de novo pelo passo 2.")


EXECUTAR = {0: passo_0, 1: passo_1, 2: passo_2, 3: passo_3, 4: passo_4, 5: passo_5}


def executar(n: int) -> None:
    print(f"\n{LINHA}\nPASSO {n} — {PASSOS[n]}\n{LINHA}")
    sit = situacao()
    faltam = [m for m in range(n) if not sit[m][0] and not (n <= 2 and m == 0)]
    if faltam:
        print("Antes deste passo falta concluir: " + ", ".join(f"{m} ({PASSOS[m]})" for m in faltam))
        return
    try:
        EXECUTAR[n]()
    except KeyboardInterrupt:
        print("\nInterrompido. O que já foi feito ficou gravado; rode o passo de novo para continuar.")
    except Exception as exc:
        print(f"\nO passo parou com erro: {type(exc).__name__}: {exc}")


def mostrar_menu() -> None:
    sit = situacao()
    seguinte = proximo(sit)
    print(f"\n{LINHA}\nRagClean — passos para colocar o RAG no ar\n{LINHA}")
    for n, nome in PASSOS.items():
        marca = "[x]" if sit[n][0] else "[ ]"
        seta = "  <- próximo" if n == seguinte else ""
        print(f" {marca} {n}. {nome:<32} {sit[n][1]}{seta}")
    print(f"\n     6. Catálogo de perguntas            {len(perguntas.carregar())} pergunta(s) — ver, importar, remover")
    print("     7. Atualizar tudo                   refaz só o que mudou (corpus ou perguntas)")
    print("     a. Ajuda: como fazer perguntas novas")
    print("     9. Recomeçar do zero                mantém os documentos originais e o catálogo")
    print("     s. Sair")
    if seguinte is None:
        print("\nTudo em dia. Use o passo 4 para novas perguntas e o 5 para validá-las.")


def principal() -> None:
    parser = argparse.ArgumentParser(description="Menu de passos do RagClean")
    parser.add_argument("--passo", type=int, choices=sorted(PASSOS), help="executa um passo e sai")
    args = parser.parse_args()
    for fluxo in (sys.stdout, sys.stderr):  # terminal do Windows: garante acentos e linhas
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    if args.passo is not None:
        executar(args.passo)
        return
    while True:
        mostrar_menu()
        seguinte = proximo(situacao())
        dica = f" (Enter = passo {seguinte})" if seguinte is not None else ""
        try:
            escolha = input(f"\nEscolha{dica}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if escolha in {"s", "sair", "q"}:
            return
        if not escolha and seguinte is not None:
            escolha = str(seguinte)
        extras = {"6": ("CATÁLOGO DE PERGUNTAS", catalogo_de_perguntas), "7": ("ATUALIZAR TUDO", atualizar_tudo),
                  "a": ("AJUDA — COMO FAZER PERGUNTAS NOVAS", ajuda_perguntas), "9": ("RECOMEÇAR", recomecar)}
        if escolha in extras:
            print(f"\n{LINHA}\n{extras[escolha][0]}\n{LINHA}")
            try:
                extras[escolha][1]()
            except KeyboardInterrupt:
                print("\nInterrompido. O que já foi feito ficou gravado.")
            except Exception as exc:
                print(f"\nParou com erro: {type(exc).__name__}: {exc}")
        elif escolha.isdigit() and int(escolha) in PASSOS:
            executar(int(escolha))
        else:
            print("Opção inválida.")
            continue
        try:
            input("\nEnter para voltar ao menu...")
        except (EOFError, KeyboardInterrupt):
            print()
            return


if __name__ == "__main__":
    principal()
