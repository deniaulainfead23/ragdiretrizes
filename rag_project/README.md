# RAG Project — Análise Documental e Recuperação Semântica

Este projeto implementa um pipeline simples para aplicar a metodologia descrita em `contexto.md`:

- Ingestão de documentos (PDFs e textos) a partir da pasta `../dados_brutos/corpus/`.
- Extração de texto com `pdfplumber` e OCR (`pytesseract`) quando necessário.
- Pré-processamento e segmentação em chunks.
- Geração de embeddings com `sentence-transformers` e indexação com `faiss`.
- Recuperação semântica e síntese (opcional) via API OpenAI.

Para não manter embeddings e índice FAISS na memória local, também é possível usar
Vector Store + File Search hospedados pela OpenAI. Esse recurso é cobrado pela API,
separadamente da assinatura do ChatGPT.

## Instalação

Recomenda-se criar um virtualenv e instalar as dependências:

```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\\Scripts\\activate no Windows
pip install -r requirements.txt
python -m nltk.downloader punkt
python -m spacy download pt_core_news_sm
```

Além disso, instale o Tesseract OCR no sistema e adicione ao PATH.

## Nova rodada para corpus curado

O executor `run_curated_pipeline.py` inicia uma rodada em uma pasta exclusiva,
sem substituir datasets, índices ou resultados anteriores. Por padrão, faz
somente a pré-auditoria do corpus e salva um manifesto com hashes em
`dados_intermediarios/pipeline_runs/<run-id>/run_manifest.json`:

```bash
python -m rag_project.run_curated_pipeline --run-id curadoria_2026_09
```

A auditoria registra divergências entre o corpus e o registro. O modo padrão
constrói somente documentos `validated`; documentos ausentes da seleção
impedem uma construção rastreável. Depois de alinhar o registro, `--build` gera
o dataset original, sua versão inglesa traduzida pela API e um índice FAISS
novo, todos dentro da pasta dessa rodada:

```bash
python -m rag_project.run_curated_pipeline --run-id curadoria_2026_09 --build
```

Para uma exploração preliminar que também inclua documentos registrados como
`pending_review`, acrescente `--include-pending-review`. O status original é
preservado; isso não aprova documentos nem suas evidências. A tradução integral
e o índice local podem exigir tempo, chamadas pagas à API e memória. Use um
identificador de rodada novo a cada execução.

A rodada exploratória de 27/09/2026 usou 94 documentos registrados dos 22 países,
preservando quatro documentos `validated` e 90 `pending_review`. Q01–Q13 foram
executadas no Vector Store OpenAI a partir dos textos originais. O TF-IDF também
foi calculado sobre o dataset multilíngue original; esses escores são exploratórios
e não permitem comparação normalizada entre idiomas. O FAISS local dessa rodada
não foi concluído por falta de memória.

## Uso

1. Construir o índice a partir do corpus (executar na pasta `rag_project`):

```bash
python build_index.py --corpus ../corpus --out indexed
```

2. Consultar o índice:

```bash
python run_query.py --index indexed --question "Como cada país define competências digitais?"
```

Para obter uma síntese gerada por um LLM, exporte `OPENAI_API_KEY` no ambiente ou passe `--openai_key`.

## Vector Store hospedado

Depois de gerar o dataset, envie o arquivo inglês para a OpenAI:

```bash
python openai_vector_store.py upload --file ../dados_intermediarios/datasets/dataset_english.jsonl
```

Guarde o `vector_store_id` retornado e consulte sem carregar FAISS:

```bash
python run_query.py --vector_store_id SEU_VECTOR_STORE_ID --question "Como cada país define competências digitais?"
```

Para consultar as perguntas estruturadas do catálogo YAML em lote usando o Vector Store:

```bash
python run_batch.py --out responses_cloud.jsonl \
    --vector_store_id SEU_VECTOR_STORE_ID --backend openai
```

O catálogo ativo está em `rag_project/questions/questions.yaml`. O antigo
`questions.txt` foi preservado em `historico-versoes/` apenas para consulta histórica.

Para hospedar os dois datasets e guardar os IDs localmente para reutilização:

```bash
python openai_vector_store.py sync --english-vector-store-id SEU_ID_INGLES
```

Na primeira execução, o dataset original será enviado e o dataset inglês reutilizará
o ID informado. Execuções seguintes reutilizam o manifesto `.openai_vector_stores.json`
e não recriam os Vector Stores.

O dataset original continua local para preservar a fonte, e o dataset inglês é usado
como base de análise e busca hospedada.

## Observações

O código é um protótipo alinhado à metodologia: adequações podem ser necessárias para lidar com formatos específicos do corpus e para melhorar chunking e normalização linguística.
