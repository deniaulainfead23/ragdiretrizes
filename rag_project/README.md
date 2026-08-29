# RAG Project — Análise Documental e Recuperação Semântica

Este projeto implementa um pipeline simples para aplicar a metodologia descrita em `contexto.md`:

- Ingestão de documentos (PDFs e textos) a partir da pasta `corpus/`.
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
python openai_vector_store.py upload --file ../corpus/dataset_output/dataset_english.jsonl
```

Guarde o `vector_store_id` retornado e consulte sem carregar FAISS:

```bash
python run_query.py --vector_store_id SEU_VECTOR_STORE_ID --question "Como cada país define competências digitais?"
```

O dataset original continua local para preservar a fonte, e o dataset inglês é usado
como base de análise e busca hospedada.

## Observações

O código é um protótipo alinhado à metodologia: adequações podem ser necessárias para lidar com formatos específicos do corpus e para melhorar chunking e normalização linguística.
