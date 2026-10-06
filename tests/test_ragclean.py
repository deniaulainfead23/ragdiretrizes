"""Testes sem internet: extração, localização de trechos e regra de validação."""
import json
from types import SimpleNamespace

import pytest

from ragclean import caminhos, consulta, extracao, indexacao, validacao

TEXTO = (
    "Computational thinking is developed across all key stages of the cur-\n"
    "riculum. Pupils should be taught to design, write and debug programs that accomplish\n"
    "specific goals, including controlling or simulating physical systems.\n\n"
    "A “high-quality” computing education equips pupils to use computational thinking and "
    "creativity to understand and change the world. " + "Texto de enchimento do documento. " * 20
)


@pytest.fixture
def projeto(tmp_path, monkeypatch):
    for nome, rel in {
        "RAIZ": "", "CORPUS": "dados_brutos/corpus", "INTERMEDIARIOS": "dados_intermediarios",
        "DERIVADOS": "dados_derivados", "TEXTOS": "dados_intermediarios/textos",
        "MANIFESTO": "dados_intermediarios/manifesto.csv", "INDICE": "dados_intermediarios/indice.json",
        "RESPOSTAS": "dados_derivados/respostas", "VALIDACAO": "dados_derivados/validacao",
    }.items():
        monkeypatch.setattr(caminhos, nome, tmp_path / rel)
    (tmp_path / "dados_brutos/corpus/reino-unido").mkdir(parents=True)
    (tmp_path / "dados_brutos/corpus/reino-unido/curriculo.txt").write_text(TEXTO, encoding="utf-8")
    (tmp_path / "dados_brutos/corpus/solto.md").write_text("Documento sobre culinária. " * 30, encoding="utf-8")
    (tmp_path / "dados_brutos/corpus/vazio.txt").write_text("quase nada", encoding="utf-8")
    (tmp_path / "dados_brutos/corpus/foto.png").write_bytes(b"\x89PNG")
    return tmp_path


def _juiz(veredito):
    saida = SimpleNamespace(output_text=json.dumps(
        {"veredito": veredito, "justificativa": "teste", "afirmacoes_sem_respaldo": []}))
    return SimpleNamespace(responses=SimpleNamespace(create=lambda **_: saida))


def test_extracao_aceita_corpus_em_qualquer_estrutura(projeto):
    lidos, ignorados = extracao.listar_corpus()
    assert len(lidos) == 3 and [a.name for a in ignorados] == ["foto.png"]
    registros = {r["origem"]: r for r in extracao.extrair_corpus(avisar=lambda *_: None)}
    assert registros["reino-unido/curriculo.txt"]["situacao"] == "ok"
    assert registros["reino-unido/curriculo.txt"]["pasta"] == "reino-unido"
    assert registros["solto.md"]["pasta"] == ""
    assert registros["vazio.txt"]["situacao"] == "sem_texto"
    assert len(list(caminhos.TEXTOS.glob("*.txt"))) == 2


def test_localiza_trecho_literal_apesar_de_quebra_de_linha_e_hifen():
    texto = validacao.limpar(TEXTO)
    achado = validacao.localizar(
        "developed across all key stages of the curriculum. Pupils should be taught to design", texto)
    assert achado["modo"] == "literal"


def test_localiza_trecho_com_aspas_diferentes_e_reticencias():
    texto = validacao.limpar(TEXTO)
    achado = validacao.localizar(
        'A "high-quality" computing education equips pupils [...] to understand and change the world', texto)
    assert achado and achado["modo"] == "literal"


def test_localiza_trecho_com_pequeno_ruido():
    achado = validacao.localizar(
        "Pupils should be taught to design, write and debug programms that accomplish specific goals",
        validacao.limpar(TEXTO))
    assert achado["modo"] == "aproximado" and achado["similaridade"] >= 90


def test_nao_localiza_conteudo_inventado_nem_trecho_curto():
    texto = validacao.limpar(TEXTO)
    assert validacao.localizar("Artificial intelligence is mandatory for every pupil from age five onwards", texto) is None
    assert validacao.localizar("computing", texto) is None


def _item(doc_id, trecho):
    return {"id": "Q", "pergunta": "p", "resposta": "r", "encontrou_resposta": True,
            "evidencias": [{"doc_id": doc_id, "documento": "x", "trecho": trecho}]}


def test_regra_de_validacao(projeto):
    registros = extracao.extrair_corpus(avisar=lambda *_: None)
    doc = next(r["doc_id"] for r in registros if r["origem"].endswith("curriculo.txt"))
    outro = next(r["doc_id"] for r in registros if r["origem"] == "solto.md")
    corpus = validacao.Corpus()
    bom = "Pupils should be taught to design, write and debug programs that accomplish"

    assert validacao.validar_item(_item(doc, bom), corpus, api=_juiz("sustentada"))["status"] == "VALIDADA"
    assert validacao.validar_item(_item(doc, bom), corpus, api=_juiz("parcial"))["status"] == "PARCIAL"
    assert validacao.validar_item(_item(doc, bom), corpus, api=_juiz("nao_sustentada"))["status"] == "NAO_VALIDADA"

    # documento citado errado, mas o conteúdo existe no corpus: vale, e fica registrado onde foi achado
    r = validacao.validar_item(_item(outro, bom), corpus, api=_juiz("sustentada"))
    assert r["status"] == "VALIDADA"
    assert r["evidencias"][0]["situacao"] == "localizado_em_outro_documento"

    # trecho inventado: reprova sem nem chamar o juiz
    inventado = "Every school must teach quantum computing in the first year of primary education"
    assert validacao.validar_item(_item(doc, inventado), corpus, api=None)["status"] == "NAO_VALIDADA"

    vazio = {"id": "Q", "pergunta": "p", "resposta": "não consta", "encontrou_resposta": False, "evidencias": []}
    assert validacao.validar_item(vazio, corpus)["status"] == "SEM_RESPOSTA_NO_CORPUS"


def test_original_alterado_deixa_de_servir_de_prova(projeto):
    registros = extracao.extrair_corpus(avisar=lambda *_: None)
    doc = next(r["doc_id"] for r in registros if r["origem"].endswith("curriculo.txt"))
    (caminhos.CORPUS / "reino-unido/curriculo.txt").write_text("outro conteúdo " * 50, encoding="utf-8")
    corpus = validacao.Corpus()
    r = validacao.validar_item(_item(doc, "Pupils should be taught to design, write and debug programs"), corpus)
    assert r["status"] == "NAO_VALIDADA"
    assert r["evidencias"][0]["situacao"] == "original_ausente_ou_alterado"


class _ApiFalsa:
    """Imita o mínimo da API da OpenAI usado na indexação e na consulta."""

    def __init__(self):
        self.enviados, self.apagados, self.pedidos = {}, [], []
        self.vector_stores = SimpleNamespace(
            create=lambda name: SimpleNamespace(id="vs_teste"),
            files=SimpleNamespace(upload_and_poll=self._enviar, delete=lambda fid, vector_store_id: None),
        )
        self.files = SimpleNamespace(delete=self.apagados.append)
        self.responses = SimpleNamespace(create=self._responder)

    def _enviar(self, vector_store_id, file, attributes):
        self.enviados[file[0]] = attributes
        return SimpleNamespace(status="completed", id="file_" + file[0])

    def _responder(self, **pedido):
        self.pedidos.append(pedido)
        doc = next(iter(self.enviados))
        return SimpleNamespace(output_text=json.dumps({
            "encontrou_resposta": True, "resposta": "Ensina-se a depurar programas.",
            "evidencias": [{"arquivo": doc, "trecho": "write and debug programs that accomplish specific goals"}]}))


def test_indexacao_incremental_e_consulta(projeto):
    extracao.extrair_corpus(avisar=lambda *_: None)
    api = _ApiFalsa()
    indice = indexacao.indexar(avisar=lambda *_: None, api=api)
    assert indice["vector_store_id"] == "vs_teste" and len(indice["arquivos"]) == 2
    assert {a.get("pasta") for a in api.enviados.values()} == {"reino-unido", None}
    assert indexacao.pendencias() == ([], [])

    # sai um documento, entra outro: só a diferença é sincronizada
    (caminhos.CORPUS / "solto.md").unlink()
    (caminhos.CORPUS / "novo.txt").write_text("Novo documento do corpus. " * 30, encoding="utf-8")
    extracao.extrair_corpus(avisar=lambda *_: None)
    enviar, retirar = indexacao.pendencias()
    assert len(enviar) == 1 and len(retirar) == 1
    indexacao.indexar(avisar=lambda *_: None, api=api)
    assert len(api.apagados) == 1 and indexacao.pendencias() == ([], [])

    rodada = consulta.rodar([{"id": "Q01", "titulo": "t", "pergunta": "O que se ensina?"}],
                            pasta="reino-unido", avisar=lambda *_: None, api=api)
    assert api.pedidos[-1]["tools"][0]["filters"] == {"type": "eq", "key": "pasta", "value": "reino-unido"}
    resultados = validacao.validar_rodada(rodada, avisar=lambda *_: None, api=_juiz("sustentada"))
    assert resultados[0]["status"] == "VALIDADA"
    assert (caminhos.VALIDACAO / f"{rodada}.csv").exists()


# ───────────── catálogo de perguntas e "atualizar tudo" ─────────────

from ragclean import atualizacao, perguntas  # noqa: E402

CATALOGO = [{"id": "Q01", "titulo": "PC", "pergunta": "Como o pensamento computacional é definido nos documentos?"},
            {"id": "Q02", "titulo": "Ética", "pergunta": "Como os documentos abordam ética digital e privacidade?"}]


@pytest.fixture
def com_catalogo(projeto, monkeypatch):
    monkeypatch.setattr(caminhos, "PERGUNTAS", projeto / "perguntas.yaml")
    monkeypatch.setattr(caminhos, "PERGUNTAS_ENTRADA", projeto / "dados_brutos/perguntas")
    (projeto / "dados_brutos/perguntas").mkdir()
    perguntas.gravar(CATALOGO)
    return projeto


def test_importa_csv_do_excel_juntando_ao_catalogo(com_catalogo):
    arq = caminhos.PERGUNTAS_ENTRADA / "novas.csv"
    arq.write_bytes("ID;Título;Pergunta\nQ02;Ética;Como os documentos abordam ética, privacidade e segurança?\n"
                    ";;Como os documentos orientam a avaliação da aprendizagem?\n"
                    ";;Como o pensamento computacional é definido nos documentos?\n".encode("latin-1"))
    assert perguntas.arquivos_para_importar() == [arq]
    prontas, erros, avisos = perguntas.conferir(perguntas.ler_arquivo(arq), perguntas.carregar())
    assert not erros
    assert [p["id"] for p in prontas] == ["Q02", "P01", "Q01"]  # sem id: código novo, ou o id de quem já tem o mesmo texto
    assert prontas[1]["titulo"].startswith("Como os documentos orientam")
    efeito = perguntas.comparar(prontas, perguntas.carregar(), substituir=False)
    assert [len(efeito[k]) for k in ("novas", "alteradas", "iguais", "removidas")] == [1, 1, 1, 0]
    assert [p["id"] for p in efeito["catalogo"]] == ["Q01", "Q02", "P01"]
    perguntas.gravar(efeito["catalogo"])
    assert perguntas.carregar()[1]["pergunta"].endswith("segurança?")
    assert list((caminhos.INTERMEDIARIOS / "perguntas_anteriores").glob("*.yaml"))  # cópia do catálogo anterior


def test_importa_txt_xlsx_e_yaml_antigo(com_catalogo):
    import openpyxl

    txt = caminhos.PERGUNTAS_ENTRADA / "a.txt"
    txt.write_text("# rascunho\nQue infraestrutura digital os documentos exigem das escolas?\n\n", encoding="utf-8")
    assert [p["pergunta"][:3] for p in perguntas.ler_arquivo(txt)] == ["Que"]
    wb = openpyxl.Workbook()
    wb.active.append(["id", "pergunta"])
    wb.active.append(["Q20", "Como os documentos tratam a formação de professores?"])
    wb.save(caminhos.PERGUNTAS_ENTRADA / "b.xlsx")
    assert perguntas.ler_arquivo(caminhos.PERGUNTAS_ENTRADA / "b.xlsx")[0]["id"] == "Q20"
    yml = caminhos.PERGUNTAS_ENTRADA / "c.yaml"
    yml.write_text("questions:\n  - question_id: Q30\n    title: T\n    question_text: Como a IA aparece no currículo oficial?\n")
    assert perguntas.ler_arquivo(yml)[0] == {"id": "Q30", "titulo": "T", "pergunta": "Como a IA aparece no currículo oficial?"}


def test_importacao_recusa_arquivo_com_problema(com_catalogo):
    ruins = [{"id": "X 1", "titulo": "", "pergunta": "Como os documentos tratam inclusão digital?"},
             {"id": "Q9", "titulo": "", "pergunta": "IA?"},
             {"id": "Q9", "titulo": "", "pergunta": "Em que página aparece a programação no currículo?"}]
    _, erros, avisos = perguntas.conferir(ruins, [])
    assert len(erros) == 3 and any("página" in a for a in avisos)
    assert perguntas.conferir([{"id": "", "titulo": "", "pergunta": ""}], [])[1]  # sem coluna 'pergunta'
    substituir = perguntas.comparar([CATALOGO[0]], CATALOGO, substituir=True)
    assert [p["id"] for p in substituir["removidas"]] == ["Q02"]


def test_atualizar_tudo_refaz_so_o_que_mudou(com_catalogo):
    api, juiz, calado = _ApiFalsa(), _juiz("sustentada"), lambda *_: None
    assert atualizacao.plano()["extrair"] and len(atualizacao.plano()["perguntas"]) == 2
    feito = atualizacao.atualizar(avisar=calado, api=api, api_juiz=juiz)
    assert len(api.pedidos) == 2 and feito["validadas"] == [feito["rodada"]]

    p = atualizacao.plano()  # nada mudou: nada a fazer, nenhuma chamada nova
    assert not (p["extrair"] or p["indexar"] or p["perguntas"] or p["validar"])
    atualizacao.atualizar(avisar=calado, api=api, api_juiz=juiz)
    assert len(api.pedidos) == 2

    # uma pergunta alterada e uma nova: só essas duas são refeitas
    catalogo = perguntas.carregar()
    catalogo[1]["pergunta"] = "Como os documentos abordam ética, privacidade e segurança?"
    perguntas.gravar(catalogo + [{"id": "Q03", "titulo": "t", "pergunta": "Como a avaliação é orientada nos documentos?"}])
    assert [q["id"] for q in atualizacao.plano()["perguntas"]] == ["Q02", "Q03"]
    import time; time.sleep(1.1)  # o nome da rodada tem resolução de 1 segundo
    atualizacao.atualizar(avisar=calado, api=api, api_juiz=juiz)
    assert len(api.pedidos) == 4

    # o corpus mudou: o índice muda e todas as perguntas voltam a ficar pendentes
    (caminhos.CORPUS / "novo.txt").write_text("Novo documento do corpus. " * 30, encoding="utf-8")
    p = atualizacao.plano()
    assert p["extrair"] and p["indexar"] and len(p["perguntas"]) == 3
    time.sleep(1.1)
    atualizacao.atualizar(avisar=calado, api=api, api_juiz=juiz)
    assert len(api.pedidos) == 7 and atualizacao.plano()["perguntas"] == []
    assert atualizacao.perguntas_pendentes(pasta="reino-unido")  # outra pasta é outro conjunto de respostas
