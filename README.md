<p align="center">
  <img src="assets/banner.svg" alt="Banner RAG Diretrizes" width="100%" />
</p>

<p align="center">
  <img src="https://avatars.githubusercontent.com/u/129794825?v=4" width="150" alt="Foto de Denise Moraes" style="border-radius:50%;" />
</p>

<h1 align="center">Denise Moraes</h1>

<p align="center">
  Professora • Pesquisadora • Tecnologia da Informação • Humanidades Digitais
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3A102D?style=for-the-badge&logo=python&logoColor=F7D5E6" />
  <img src="https://img.shields.io/badge/RAG-6B204E?style=for-the-badge&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/PLN-8E2F68?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Educação_Comparada-B85D91?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Humanidades_Digitais-D88AB3?style=for-the-badge" />
</p>

## Sobre o projeto

Este repositório reúne o desenvolvimento da pesquisa **RAG Diretrizes**, voltada à análise comparativa de diretrizes curriculares internacionais da Educação Básica, com atenção especial à Computação, Educação Digital, Pensamento Computacional e às competências necessárias à formação do cidadão contemporâneo.

A proposta integra métodos de **Educação Comparada**, **Humanidades Digitais**, **Ciência de Dados**, **Processamento de Linguagem Natural** e **Retrieval-Augmented Generation (RAG)** para organizar, consultar e analisar documentos curriculares de diferentes países.

## Objetivo da pesquisa

Construir uma base documental e computacional capaz de apoiar a comparação entre diretrizes educacionais internacionais, identificando convergências, diferenças, competências, habilidades e abordagens relacionadas à formação digital na Educação Básica.

A análise considera também a relação desses documentos com referenciais brasileiros, especialmente a **BNCC** e o **Complemento à BNCC Computação**.

## Eixos de análise

- Computação na Educação Básica
- Educação Digital
- Pensamento Computacional
- Cultura Digital
- Cidadania Digital
- Competências e habilidades
- Formação integral
- Educação Comparada
- Humanidades Digitais
- Políticas curriculares internacionais

## Metodologia computacional

O projeto utiliza uma arquitetura baseada em recuperação e análise de documentos para permitir consultas fundamentadas diretamente no corpus da pesquisa.

```text
Documentos oficiais
        ↓
Extração e tratamento de texto
        ↓
Normalização e organização do corpus
        ↓
Segmentação dos documentos
        ↓
Embeddings / representação textual
        ↓
Indexação vetorial (OpenAI Vector Store como principal; FAISS local como fallback)
        ↓
RAG rastreável
        ↓
Consulta, comparação e análise documental + lexical
```

Também são exploradas técnicas complementares de análise textual, como **TF-IDF**, frequência de termos, similaridade textual, mineração de texto e classificação temática.

## Estado atual do projeto

A implementação atual está organizada em fases metodológicas e passa por um pipeline em que cada camada tem papel específico:

- Análise documental e bibliográfica: organização do corpus, metadados e rastreabilidade;
- Frameworks e regras de processamento: definição dos eixos de análise, stopwords e entidades excluídas;
- Análise lexical exploratória: TF-IDF, similaridade textual e gráficos de apoio;
- Backend vetorial: `openai` como backend principal e `local` como fallback;
- Matriz de evidências: rastreio de indicadores por documento, país e dimensão;
- Sensibilidade do pipeline: verificação de consistência dos resultados obtidos;
- RAG rastreável: recuperação semântica com evidência documental e metadata associada.

## Auditoria, validação e reprodutibilidade

A curadoria do corpus possui uma camada específica de auditoria para permitir comprovação e repetição do processo.

Principais artefatos:

- `OCR_Seletivo_Corpus_RAG.ipynb` — notebook histórico do OCR seletivo aplicado aos documentos bloqueados;
- `Auditoria_Reutilizavel_Corpus_RAG.ipynb` — notebook Colab consolidado para repetir auditoria, OCR, revisão por página e validação do JSONL;
- `rag_project/audit_corpus.py` — auditoria automatizada e reutilizável do catálogo, textos processados e dataset de conteúdo;
- `docs/PROTOCOLO_VALIDACAO_TEXTOS.md` — método passo a passo para validação textual orientada por exceções e reutilização por outros pesquisadores.

Execução local:

```bash
python -m rag_project.audit_corpus --all
```

Relatórios esperados:

```text
analysis/audit/audit_summary.json
analysis/audit/processed_page_audit.csv
```

O protocolo preserva os documentos originais, mantém `document_id` e páginas, aplica OCR apenas quando necessário, registra páginas suspeitas para revisão humana e valida a estrutura dos dados antes da indexação vetorial.

## Regras metodológicas do projeto

> A análise lexical não substitui a leitura documental nem a interpretação crítica do pesquisador.

- O TF-IDF e a similaridade textual são usados como ferramentas exploratórias.
- O corpus principal contém 22 países. UNESCO e PISA/OCDE são referências internacionais e não entram na contagem de países nem no bloco comparativo nacional.
- Os resultados computacionais devem ser lidos como pistas de vocabulário e proximidade textual, e não como prova de equivalência curricular.
- A recuperação semântica e o RAG devem retornar evidências vinculadas a documento, país, fonte e categoria analítica.
- Páginas marcadas como vazias, curtas ou de baixa qualidade devem ser revisadas visualmente antes da liberação.
- A ausência de recuperação semântica não deve ser interpretada automaticamente como ausência conceitual no documento.

## Tecnologias

| Área | Tecnologias e métodos |
|---|---|
| Linguagem | Python |
| Recuperação de informação | RAG |
| PLN | tokenização, embeddings, similaridade e análise textual |
| Análise lexical | TF-IDF e frequência de termos |
| Dados | Pandas e estruturas tabulares |
| Corpus | documentos curriculares oficiais |
| Auditoria textual | PyMuPDF, Tesseract OCR, validação por página e revisão humana |
| Pesquisa | análise documental e Educação Comparada |
| Ambiente | VS Code, Google Colab e GitHub |

## Estrutura planejada

```text
ragdiretrizes/
│
├── assets/             # identidade visual do projeto
├── corpus/             # documentos curriculares
├── rag_project/        # implementação do sistema RAG e auditoria
├── analysis/           # relatórios e resultados de auditoria/análise
├── docs/               # documentação metodológica e protocolos
├── resultados/         # tabelas e resultados de análise
├── traducoes/          # versões de apoio em português
├── notebooks/          # experimentos e análises
└── README.md
```

## Pesquisa acadêmica

O projeto faz parte de uma investigação acadêmica na interface entre **Educação, Tecnologia da Informação e Humanidades Digitais**.

Minha formação e atuação estão relacionadas à Tecnologia da Informação, à docência e à pesquisa. Sou Mestre em Desenvolvimento Local e desenvolvo estudos em Humanidades Digitais na UFRRJ, utilizando métodos computacionais para investigação de documentos educacionais e políticas curriculares.

## Princípio da pesquisa

> Tecnologia aplicada à pesquisa educacional deve ampliar a capacidade de análise sem substituir a leitura crítica, a interpretação do pesquisador e a verificação das fontes.

## Autoria

**Denise Moraes**  
Professora e Pesquisadora  
Tecnologia da Informação • Educação • Humanidades Digitais

<p align="center">
  <sub>Pesquisa, educação e tecnologia conectadas por dados, documentos e análise crítica.</sub>
</p>
