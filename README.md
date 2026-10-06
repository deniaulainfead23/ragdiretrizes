# RagClean

Versão enxuta do RAG de diretrizes curriculares. Você coloca os documentos numa pasta,
segue um menu de passos e obtém respostas validadas pelo conteúdo dos documentos originais.

Esta branch (`ragclean`) parte de `correcao-pipeline-rag`, que continua intacta e guarda
todo o histórico anterior (scripts, rodadas, análises TF-IDF e DLGF).

## Começar

```bash
git fetch origin
git checkout ragclean
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python iniciar.py
```

## O menu

`python iniciar.py` mostra os passos, o que já foi feito e qual é o próximo. Cada passo
explica o que vai fazer antes de executar. Enter executa o próximo passo pendente.

| Passo | O que faz | Onde grava | Custo |
|---|---|---|---|
| 0. Preparar o ambiente | Confere bibliotecas e a chave no `.env` | `.env` | — |
| 1. Conferir o corpus | Lista os documentos encontrados | — | — |
| 2. Extrair o texto | Lê cada documento e grava o texto | `dados_intermediarios/textos/`, `manifesto.csv` | — |
| 3. Indexar | Envia os textos ao Vector Store da OpenAI | `dados_intermediarios/indice.json` | API |
| 4. Perguntar | Pergunta livre ou catálogo `ragclean/perguntas.yaml` | `dados_derivados/respostas/` | API |
| 5. Validar | Confere as respostas contra os documentos originais | `dados_derivados/validacao/` | API |
| 9. Recomeçar | Apaga índice, intermediários e derivados | — | — |

Para rodar um passo direto, sem o menu: `python iniciar.py --passo 2`.

## Corpus livre

Coloque os documentos em `dados_brutos/corpus/`, em qualquer ordem e em qualquer estrutura
de pastas. Não há manifesto manual nem registro por país. Formatos: PDF, DOCX, TXT, MD, HTML.

- Acrescentou, trocou ou removeu documentos? Rode os passos 2 e 3 de novo: só a diferença é processada.
- Se usar subpastas, a primeira pasta vira um filtro opcional no passo 4 (ex.: perguntar só sobre `brasil/`).
- PDFs escaneados (imagem, sem texto) são apontados no passo 2 e ficam fora do RAG até receberem OCR.
- Os documentos não vão para o git.

## Como a validação funciona

Não há conferência por número de página. A pergunta é só uma: **o conteúdo da resposta tem
respaldo nos documentos originais do corpus?**

1. **Localização do trecho.** O RAG é obrigado a citar trechos copiados dos documentos. Cada
   trecho é procurado no texto inteiro do documento original — primeiro no documento citado,
   depois nos demais. A busca ignora diferenças de quebra de linha, hifenização e aspas, e
   aceita pequeno ruído de extração (similaridade ≥ 90%).
2. **Juiz semântico.** Um LLM recebe a resposta e as passagens localizadas (com contexto) e
   diz se a resposta é sustentada por elas, sem usar conhecimento externo.

| Status | Significado |
|---|---|
| `VALIDADA` | Há trecho localizado no original e a resposta é sustentada por ele |
| `PARCIAL` | Há respaldo, mas alguma afirmação relevante ficou sem apoio (listada no resultado) |
| `NAO_VALIDADA` | Nenhum trecho foi localizado, ou o conteúdo central não tem respaldo |
| `SEM_RESPOSTA_NO_CORPUS` | O RAG informou que o corpus não trata do assunto |

Antes de validar, o hash de cada documento original é comparado com o registrado na extração.
Se o original mudou ou sumiu, ele deixa de servir de prova até os passos 2 e 3 serem refeitos.

O `.csv` da validação traz uma linha por pergunta; o `.json` traz cada trecho, onde foi
localizado e a passagem do original.

## Estrutura

```
iniciar.py               menu
ragclean/
  extracao.py            passos 1 e 2
  indexacao.py           passo 3
  consulta.py            passo 4
  validacao.py           passo 5
  menu.py
  perguntas.yaml         catálogo Q01–Q14
dados_brutos/corpus/     documentos originais (você preenche)
dados_intermediarios/    textos extraídos, manifesto, índice
dados_derivados/         respostas e validações
tests/                   pytest, roda sem internet
```

## Configuração opcional (`.env`)

`RAG_MODELO` e `RAG_MODELO_JUIZ` (padrão `gpt-4o-mini`), `RAG_MAX_TRECHOS` (padrão 12).
