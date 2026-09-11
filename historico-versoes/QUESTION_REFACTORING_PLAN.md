# Plano de refatoração do sistema de perguntas do RAG

## 1. Estrutura atual observada

O projeto já possui uma lista de perguntas em [rag_project/questions.txt](../rag_project/questions.txt) e um executor genérico em [rag_project/run_query.py](../rag_project/run_query.py), além da integração com Vector Store em [rag_project/openai_vector_store.py](../rag_project/openai_vector_store.py).

### Estado atual

- [rag_project/questions.txt](../rag_project/questions.txt) contém 15 perguntas em linguagem natural.
- Essas perguntas são amplas, genéricas e em muitos casos induzem rankings ou conclusões agregadas.
- O arquivo é usado como uma lista linear de prompts, sem identificação de:
  - question_id;
  - framework;
  - categoria UNESCO;
  - país alvo;
  - tipo de pergunta;
  - exigência de evidência validada;
  - versionamento.

O código atual de consulta também ainda prioriza uma interação livre com o sistema, sem exigir metadados mínimos de rastreabilidade documental.

---

## 2. Problemas encontrados

### 2.1 Perguntas ambíguas e propensas a ranking

Perguntas como:

- "Quais países têm maior alinhamento..."
- "Quais países estão mais próximos do perfil do cidadão global..."

induzem conclusões agregadas e ranking simplista. Isso contraria o princípio metodológico da dissertação.

### 2.2 Ausência de estrutura analítica

As perguntas atuais não distinguem:

- recuperação de evidência;
- classificação por categoria;
- comparação validada;
- síntese interpretativa.

### 2.3 Falta de rastreabilidade exigida

O sistema atual não exige que cada resposta seja vinculada a:

- documento;
- página;
- chunk;
- categoria UNESCO;
- país;
- tipo de correspondência (lexical ou semântica);
- validação humana.

### 2.4 Conflito com a metodologia da UNESCO

A estrutura atual não separa claramente:

- UNESCO 2015 (framework conceitual principal);
- UNESCO 2021 (expansão prospectiva);
- categorias F01-F12;
- documento de origem da categoria;
- evidência documental legítima.

### 2.5 Falta de regras contra falso positivo

As perguntas atuais podem retornar respostas baseadas apenas em termos genéricos como "global", "technology" ou "collaboration" sem contexto curricular adequado.

---

## 3. Nova estrutura proposta

A nova estrutura será organizada em [rag_project/questions/](../rag_project/questions) e será versionada com `questions_version: 2.0`.

### Arquivo principal

- [rag_project/questions/questions.yaml](../rag_project/questions/questions.yaml) (preferência)

### Estrutura de cada pergunta

Cada item terá campos como:

- question_id
- title
- question_text
- question_type
- analysis_stage
- framework
- category_id
- target_scope
- target_country
- required_metadata
- expected_output
- evidence_rule
- exclusion_rule
- allow_cross_country_comparison
- requires_validated_evidence
- notes
- version

### Tipos de pergunta

1. `evidence_retrieval`
   - localizar trechos e documentos relevantes;
   - não gerar ranking.

2. `category_analysis`
   - organizar evidências por categoria UNESCO.

3. `validated_comparison`
   - comparar apenas evidências previamente recuperadas e validadas.

4. `synthesis`
   - produzir síntese interpretativa usando evidências organizadas.

### Estágios de análise

- `retrieval`
- `classification`
- `comparison`
- `synthesis`

---

## 4. Ordem da implementação

### Ordem correta

A ordem correta é a seguinte:

1. Fase 1: auditoria e desenho metodológico
2. Fase 2: proveniência e metadados
3. Refatoração do sistema de perguntas
4. Fase 3: framework UNESCO e stopwords
5. Fase 4: TF-IDF e análise exploratória
6. Fase 5: embeddings e Vector Store principal
7. Fase 6: evidence matrix e RAG rastreável
8. demais fases metodológicas

### Conclusão sobre a ordem

A refatoração das perguntas deve ser executada antes da implementação final da Fase 3 de framework/stopwords em termos de arquitetura do rascunho operacional, porque as perguntas precisam ser organizadas a partir das categorias UNESCO e da regra de evidência. Porém a refatoração não deve ser uma substituição destrutiva do código atual; ela deve ser implementada como camada versionada e compatível.

Em outras palavras:

- o plano da refatoração deve vir antes da refatoração funcional;
- a implementação do framework UNESCO deve alimentar as perguntas;
- as perguntas não devem ser criadas apenas como prompts genéricos, mas como artefatos metodológicos versionados.

---

## 5. Arquivos a criar

- [rag_project/questions/questions.yaml](../rag_project/questions/questions.yaml)
- [rag_project/questions/](../rag_project/questions): diretório para os artefatos da nova estrutura
- [analysis/questions/](../analysis/questions): diretório de resultados de execução
- [docs/QUESTION_REFACTORING.md](QUESTION_REFACTORING.md)
- [tests/test_questions_schema.py](../tests/test_questions_schema.py)
- [tests/test_question_runner.py](../tests/test_question_runner.py)
- [tests/test_rag_evidence_output.py](../tests/test_rag_evidence_output.py)
- [tests/test_no_ranking_questions.py](../tests/test_no_ranking_questions.py)
- [tests/test_non_evidence_rule.py](../tests/test_non_evidence_rule.py)

---

## 6. Arquivos a alterar

- [rag_project/questions.txt](../rag_project/questions.txt): manter como legado, marcado e preservado
- [rag_project/run_query.py](../rag_project/run_query.py): adaptar para aceitar schema estruturado e exigências de rastreabilidade
- [rag_project/openai_vector_store.py](../rag_project/openai_vector_store.py): permitir filtro por país, documento, framework e metadata
- [README.md](../README.md): incluir novo sistema de perguntas e a regra de evidência

---

## 7. Compatibilidade e preservação

A compatibilidade deve ser preservada da seguinte forma:

- o arquivo atual [rag_project/questions.txt](../rag_project/questions.txt) continua existindo;
- ele será identificado como legado;
- opcionalmente, será copiado para `archive/questions_legacy.txt`;
- o novo sistema será centralizado em [rag_project/questions/questions.yaml](../rag_project/questions/questions.yaml);
- o executor antigo pode continuar funcionando para fins de compatibilidade temporária.

---

## 8. Riscos

- refatorar sem framework versionado;
- permitir ranking aglomerado em perguntas de retrieval;
- perder compatibilidade com o executor atual;
- gerar respostas sem document_id, page e source_text;
- misturar evidência lexical com evidência substantiva;
- não registrar `not_detected` e `inconclusive` corretamente;
- usar OpenAI Vector Store sem filtros e sem rastreabilidade.

---

## 9. Conclusão do plano

O projeto deve deixar de tratar as perguntas como prompts genéricos e passar a tratá-las como artefatos metodológicos estruturados, versionados e orientados por evidência documental.

A refatoração das perguntas é uma camada essencial antes da implementação final de framework e evidência, mas ela deve ser feita de forma incremental e compatível com o sistema já existente.

Este plano foi criado como etapa preparatória e não substitui a implementação funcional.
