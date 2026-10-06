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
