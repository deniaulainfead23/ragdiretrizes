"""Caminhos das três camadas de dados."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

BRUTOS = RAIZ / "dados_brutos"
INTERMEDIARIOS = RAIZ / "dados_intermediarios"
DERIVADOS = RAIZ / "dados_derivados"

CORPUS = BRUTOS / "corpus"
TEXTOS = INTERMEDIARIOS / "textos"
MANIFESTO = INTERMEDIARIOS / "manifesto.csv"
INDICE = INTERMEDIARIOS / "indice.json"
RESPOSTAS = DERIVADOS / "respostas"
VALIDACAO = DERIVADOS / "validacao"

PERGUNTAS = Path(__file__).resolve().parent / "perguntas.yaml"
PERGUNTAS_ENTRADA = BRUTOS / "perguntas"
AJUDA_PERGUNTAS = RAIZ / "COMO_FAZER_PERGUNTAS.md"
REFERENCIAS = BRUTOS / "referencias"
TFIDF = DERIVADOS / "tfidf"
STOPWORDS = Path(__file__).resolve().parent / "stopwords.txt"
AJUDA_TFIDF = RAIZ / "COMO_COMPARAR_TFIDF.md"
