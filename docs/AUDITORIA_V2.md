# Auditoria V2 do repositório RAG Diretrizes

## Status da auditoria

Esta é a Fase 1 do remodelamento metodológico proposto. O objetivo foi auditar a estrutura real do projeto, preservar o que já funciona e identificar os pontos críticos para a migração incremental para um pipeline científico, rastreável e defensável.

Atenção: nenhuma alteração destrutiva foi aplicada ao código funcional, ao corpus bruto, aos datasets já existentes ou aos scripts originais. A implementação de fases posteriores foi suspensa até revisão desta auditoria.

---

## 1. Estrutura atual do repositório

O repositório possui uma base funcional em Python com foco em:

- organização do corpus por país;
- extração de texto de PDFs/HTML/TXT;
- dataset bilingue para análise;
- TF-IDF e similaridade lexical;
- indexação local em FAISS;
- consulta por RAG local;
- integração parcial com OpenAI para tradução e Vector Store.

Estrutura observada:

- [README.md](../README.md): apresentação do projeto e visão geral acadêmica.
- [DOCUMENTACAO_METODOLOGICA.md](../DOCUMENTACAO_METODOLOGICA.md): documentação metodológica da pesquisa.
- [contexto.md](../contexto.md): contexto e objetivos da pesquisa, com desenho original do problema.
- [corpus/](../corpus): material documental bruto e arquivos de apoio.
- [docs/](.): documentação complementar e materiais metodológicos.
- [rag_project/](../rag_project): núcleo computacional do projeto.
- [tests/](../tests): testes automatizados existentes.

A organização atual é coerente para um protótipo acadêmico, mas ainda não está alinhada ao desenho metodológico recomendado para uma pesquisa comparativa internacional robusta.

---

## 2. Scripts existentes e dependências

### Scripts principais

- [rag_project/build_dataset.py](../rag_project/build_dataset.py)
  - gera datasets em idioma original e em inglês;
  - usa OpenAI para tradução opcional;
  - mantém o corpus original e o dataset de análise separado;
  - já implementa uma lógica de cache de tradução.

- [rag_project/build_index.py](../rag_project/build_index.py)
  - constrói índice local em FAISS;
  - faz chunking por página/documento;
  - salva checkpoint de progresso;
  - possui recuperação de estado e tolerância a falhas parcial.

- [rag_project/openai_vector_store.py](../rag_project/openai_vector_store.py)
  - implementa upload e consulta em Vector Store da OpenAI;
  - mantém manifesto local para reutilização de IDs;
  - já é o ponto de partida para a arquitetura objetivo.

- [rag_project/analyze_tfidf.py](../rag_project/analyze_tfidf.py)
  - calcula TF-IDF, similaridade entre grupos e gráficos;
  - inclui comparação entre países e UNESCO;
  - ainda usa a linguagem de "proximidade com UNESCO" que precisa ser reformulada metodologicamente.

- [rag_project/rag/indexer.py](../rag_project/rag/indexer.py)
  - indexador local com SentenceTransformers + FAISS;
  - representa a arquitetura local que deve ser mantida apenas como backend opcional ou fallback.

- [rag_project/rag/query.py](../rag_project/rag/query.py)
  - consulta local e busca semântica;
  - funcional, mas não com rastreabilidade rigorosa por documento/page/chunk e framework.

### Dependências detectadas

O projeto já depende de:

- Python;
- pandas / numpy / scikit-learn;
- sentence-transformers;
- faiss;
- openai;
- python-dotenv;
- pdfplumber / OCR e bibliotecas auxiliares;
- matplotlib para visualizações.

O risco técnico principal não é a ausência de librarias, mas a coexistência de múltiplos paradigmas sem separação clara entre:

- análise local;
- busca semântica em OpenAI Vector Store;
- dados metodológicos e evidências;
- rastreabilidade documental.

---

## 3. Fluxo atual do sistema

O fluxo existente pode ser resumido assim:

1. coleta de documentos em [corpus/](../corpus);
2. extração de texto via scripts do projeto;
3. geração de dataset original e dataset inglês em [corpus/dataset_output/](../corpus/dataset_output);
4. construção de índices locais com FAISS;
5. análise lexical com TF-IDF;
6. comparação por similaridade textual entre grupos;
7. uso de OpenAI para tradução e eventualmente para consulta em Vector Store;
8. recuperação de respostas por RAG local ou via Vector Store; 
9. geração de gráficos e tabelas analíticas.

Esse fluxo tem valor funcional e deve ser preservado como base de compatibilidade, mas ele ainda conflita com a metodologia desejada:

- a UNESCO não está formalizada como framework analítico versionado;
- o TF-IDF funciona como proxy de alinhamento sem diferenciação clara entre lexical, semântico e evidência documental;
- a recuperação semântica não está submetida a rastreabilidade documental obrigatória;
- o corpus não foi reestruturado em layers RAW/NORMALIZED/TRANSLATED/ANALYTICAL;
- o país não recebe perfil multidimensional por categoria UNESCO e não há matriz de evidências com classificação explícita.

---

## 4. Problemas metodológicos centrais

### 4.1 Tratamento insuficiente da UNESCO

O projeto atual trata a UNESCO como um conjunto de documentos comparáveis por similaridade textual, mas não como um framework analítico pré-definido e versionado. Isso é incompatible com a regra metodológica exigida: categorias devem ser construídas a priori a partir dos documentos UNESCO e não emergirem apenas da frequência lexical do corpus nacional.

Conclusão: o projeto precisa de um framework UNESCO explícito, com:

- categoria por dimensão;
- fonte documental origem;
- definição em português e inglês;
- keywords literais UNESCO e termos de expansão computacional separados;
- regras de evidência e exclusão;
- gestão de versão.

### 4.2 Uso indevido de TF-IDF como indicador substantivo

A arquitetura atual usa TF-IDF como ferramenta de comparação de proximidade entre documentos e grupos. Isso é útil para análise exploratória lexical, mas não pode ser tratado como prova de alinhamento curricular, cidadania global, qualidade formativa ou competência. Isso está em conflito direto com a exigência da pesquisa.

### 4.3 Risco de confundir frequência com competência

A regra metodológica correta é clara: "TERMO ENCONTRADO != COMPETÊNCIA COMPROVADA". O código e as análises atuais ainda permitem esse tipo de inferência indireta, especialmente quando a comparação usa termos isolados ou similaridade geral de documentos.

### 4.4 PISA como validador indevido

O repositório atual ainda faz uso do PISA como parte estrutural do thinking comparativo, mas sem a separação metodológica necessária. O PISA deve permanecer como critério de seleção e variável contextual, não como validador de alinhamento UNESCO.

### 4.5 Falta de rastreabilidade por evidência

Os scripts atuais não garantem que a resposta final consiga responder, de forma auditável, perguntas do tipo:

- qual documento sustenta a classificação?
- em qual página?
- em qual chunk?
- qual foi a categoria UNESCO?
- o texto foi original ou traduzido?
- qual foi a versão do framework?
- qual foi o processo de pré-processamento?

Sem isso, a pesquisa não consegue atender ao critério de aceitação do pipeline científico proposto.

---

## 5. Problemas técnicos e de arquitetura

### 5.1 Dependência forte de índice local

O projeto atual privilegia o uso local de FAISS em [rag_project/rag/indexer.py](../rag_project/rag/indexer.py) e [rag_project/build_index.py](../rag_project/build_index.py). Isso é funcional para pequenos experimentos, mas é um problema para o cenário descrito: corpus grande, RAM limitada e necessidade de reprodutibilidade.

A arquitetura recomendada no roteiro é a seguinte:

- local: organização, hashes, metadata, TF-IDF, framework, CSVs, matrices e gráficos;
- OpenAI Vector Store: armazenamento e recuperação semântica vetorial;
- FAISS: opcional local, não principal.

### 5.2 Arquitetura sem camada de backend

O projeto ainda não possui uma abstração explícita de backend vetorial:

- vector_backend = openai | local

Sem isso, o código mistura local e cloud, e dificultam testes, auditoria e reuso em diferentes ambientes.

### 5.3 Falta de manifesto de infraestrutura e rastreabilidade de execução

Não existe ainda um registro explícito de:

- backend vetorial utilizado;
- vector_store_id;
- modelo e dimensão de embeddings;
- framework_version;
- corpus_version;
- timestamp de execução;
- SHA256 do corpus e dos artefatos.

Isso compromete a reprodutibilidade.

### 5.4 Corpus sem camada de estados

O diretório [corpus/](../corpus) ainda não foi reorganizado em:

- raw;
- normalized;
- translated;
- analytical.

Isso é importante para preservar o bruto e permitir comparações sensíveis de preprocessing.

### 5.5 Pandas/CSV e resultados analíticos ainda não organizados como artefatos científicos

Há resultados localizados, mas sem uma estrutura clara de:

- bibliographic_matrix;
- country_selection;
- preprocessing_log;
- evidence_matrix;
- country_framework_profile;
- sensitivity_results;
- run_manifest.

Sem esses artefatos, a hipótese e os resultados não podem ser revalidados.

---

## 6. Componentes reutilizáveis

Os seguintes componentes têm valor e devem ser preservados:

### 6.1 Estrutura por país e por documento

A organização do corpus por país e o uso de pastas por jurisdição são úteis e não devem ser descartados.

### 6.2 Extração de texto

A lógica em [rag_project/build_dataset.py](../rag_project/build_dataset.py) para extrair texto de arquivos PDF/HTML/TXT é um bom ponto de partida.

### 6.3 Cache de tradução

A implementação de `translation_cache.json` é uma boa prática e deve ser mantida, com registro mais estruturado de metadados e hashes.

### 6.4 Checkpoint de indexação

A funcionalidade de checkpoint em [rag_project/build_index.py](../rag_project/build_index.py) deve ser mantida, adaptada e integrada ao processo de sincronização com Vector Store.

### 6.5 OpenAI Vector Store inicial

O módulo [rag_project/openai_vector_store.py](../rag_project/openai_vector_store.py) já aponta no caminho certo: ele cria a ideia de vector store externo para reduzir carga local, preserva IDs e pode ser expandido para um backend formal.

### 6.6 Estrutura de dataset bilingue

A existência de `dataset_original.jsonl` e `dataset_english.jsonl` é útil e deve continuar, mas exigirá metadados rígidos de rastreabilidade e hash.

---

## 7. Componentes a refatorar

### 7.1 Arquitetura de embeddings

A solução atual fica presa ao modelo local `all-MiniLM-L6-v2` em [rag_project/rag/indexer.py](../rag_project/rag/indexer.py). Isso é aceitável para testes locais, mas não deve ser arquitetura principal da pesquisa. A regra metodológica exige o uso principal do Vector Store da OpenAI para recuperação semântica.

### 7.2 TF-IDF e análise de similaridade

O TF-IDF tem papel exploratório, mas o uso atual ainda se aproxima de ranking substantivo. Precisa ser rebatizado e reorientado para:

- similariade lexical entre corpora;
- comparação de vocabulário;
- inspeção exploratória de padrões;
- apoio à recuperação de evidências, nunca como prova final.

### 7.3 Pipeline de RAG

A consulta atual não exige rastreabilidade por documento e página. O RAG deve devolver evidências contendo:

- document_id;
- title;
- country;
- page;
- chunk_id;
- source_text;
- semantic_score;
- category_id.

### 7.4 Documentação metodológica

A documentação atual ainda expressa a lógica de pesquisa antiga, em que similaridade textual é tratada mais livremente. Necessita revisão explícita para incorporar:

- framework UNESCO;
- regra da evidência;
- critério de decisão por categoria;
- separação entre lexical, semântico e documental;
- uso correto do PISA;
- uso correto de TF-IDF;
- uso principal do Vector Store da OpenAI.

---

## 8. Arquivos novos necessários para a Fase 2

Os arquivos abaixo são exigidos para a migração metodológica e devem ser implementados em ordem preservando o atual pipeline funcional:

- [metadata/](../metadata) ou equivalente: bibliographic_matrix.csv, country_selection.csv, preprocessing_log.csv, run_manifest.json
- [framework/](../framework): unesco_framework.csv, computing_framework.csv, framework_notes.md
- [config/](../config): stopwords_language.txt, stopwords_documental.txt, excluded_entities.txt, preprocessing_rules.yaml
- [analysis/](../analysis): lexical/, semantic/, unesco_alignment/, evidence/, sensitivity/, contextual/pisa/, brazil_profile/
- [logs/](../logs): registros operacionais por execução
- [archive/](../archive): artefatos antigos e exploratórios marcados como deprecated
- [metadata/vector_store_manifest.json](../metadata/vector_store_manifest.json): manifesto do backend vetorial, se a arquitetura OpenAI for ativada

Esses artefatos são necessários para garantir rastreabilidade e reprodução, e não apenas para armazenamento de dados.

---

## 9. Plano de migração recomendado

### Fase 1 (concluída na auditoria)

- auditar o repositório atual;
- preservar os scripts e o corpus;
- definir a linha de base metodológica;
- documentar riscos e estratégia de migração.

### Fase 2

- implementa proviência e matriz bibliográfica;
- adicionar hashes e manifestos;
- registrar seleção dos países e critérios de inclusão;
- adicionar metadados básicos e rastreabilidade por documento.

### Fase 3

- construir framework UNESCO versionado;
- criar stopwords em arquivos separados por categoria;
- definir regras de filtragem e registro de decisões.

### Fase 4

- refatorar TF-IDF para papel exploratório;
- renomear outputs e gráficos;
- separar análise lexical de análise documental.

### Fase 5

- criar backend vetorial com abstração `openai | local`;
- tornar o Vector Store da OpenAI o backend principal;
- manter FAISS apenas como backend local opcional ou fallback.

### Fase 6

- construir matriz de evidências;
- criar RAG rastreável;
- incluir validação humana e revisão manual.

### Fase 7

- executar sensibilidade do pipeline;
- gerar relatórios comparativos e gráficos válidos metodologicamente;
- documentar impacto da escolha de preprocessing e traduções.

### Fase 8

- atualizar README.md e DOCUMENTACAO_METODOLOGICA.md;
- adicionar testes de rastreabilidade e preventivos;
- validar que o vínculo entre documento, página, trecho, categoria e framework está íntegro.

---

## 10. Riscos de quebrar funcionalidades

Os principais riscos de migração são:

1. quebra da compatibilidade com scripts existentes;
2. perda de arquivos ou corpus sem rastreabilidade;
3. mudança de semântica do TF-IDF sem revisão metodológica;
4. uso indevido de OpenAI em um pipeline que ainda depende de arquivos locais;
5. duplicação de dados entre corpus bruto e corpus analítico;
6. fragmentação da documentação sem atualizar a metodologia;
7. perda do checkpoint de indexação local;
8. geração de artefatos com metadados incompletos;
9. substituição de tecnologia local por cloud sem manifesto de execução;
10. inferência inadequada de competência a partir de similares lexicalmente próximos.

Esses riscos são gerenciáveis desde que a migração seja incremental, preservando o que já funciona e adicionando camadas de rastreabilidade em vez de substituição radical.

---

## 11. Recomendação metodológica final da auditoria

A partir desta revisão, a arquitetura mais adequada é a seguinte:

- TF-IDF: local, exploratório, lexical e sempre interpretado como análise complementar;
- Vector Store da OpenAI: principal infraestrutura para embeddings, busca semântica e RAG;
- framework UNESCO: local, versionado, explicitamente definido e rastreável;
- matriz de evidências: local, estruturada e validada por humanos;
- PISA: critério de seleção e variável contextual, não validador do alinhamento UNESCO;
- FAISS: backend opcional local ou fallback para testes pequenos.

Em outras palavras, o projeto deve manter controle científico local sobre corpus, metadados, framework, evidências e decisão final, enquanto terceiriza a parte vetorial pesada para a infraestrutura da OpenAI. Isso reduz consumo de memória local e torna a metodologia mais defensável, reprodutível e auditável.

---

## 12. Conclusão da Fase 1

A auditoria confirma que o projeto já possui uma base técnica funcional e parcialmente alinhada à proposta de pesquisa, mas ainda não atende ao desenho metodológico exigido para uma análise documental internacional rigorosa. A principal reformulação necessária não é apagar o que existe, e sim separar corretamente:

- pesquisa documental;
- análise lexical exploratória;
- busca semântica vetorial;
- recuperação com evidência rastreável;
- decisão substantiva humana.

Até que esta auditoria seja revisada, não serão implementadas as fases seguintes.
