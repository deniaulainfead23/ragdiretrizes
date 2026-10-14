# LEIAME — Pré-classificação de Evidências e Respostas RAG por Juiz Semântico (LLM-as-a-Judge)

**Data da rodada:** 12 de outubro de 2026  
**Período de execução:** Início às `20:41:48 UTC` e término às `21:04:21 UTC` (17:41 às 18:04 pelo horário de Brasília, UTC-3)  
**Modelo avaliador:** `gpt-4o-mini` (Snapshot exato retornado pela API: `gpt-4o-mini-2024-07-18`)  
**Temperatura:** `0.0` (determinística)  
**Prompt versionado:** [juiz_semantico_v1.md](../../../../prompts/juiz_semantico_v1.md)

---

## 1. Natureza do Procedimento e Nomenclatura

Este procedimento constitui uma **pré-classificação sugerida pelo modelo de linguagem** (*LLM-as-a-judge*), com o propósito de auditar a sustentação factual de citações e respostas em nível preliminar.

- Os status gerados são estritamente **"sugeridos pelo modelo"** e registrados na coluna `llm_suggested_status`.
- As colunas de validação científica da pesquisadora (`human_classification`, `human_validation_status`, `validated_by`, `validated_at`) **permanecem intactas e vazias** nos arquivos de validação humana do repositório.
- A validação científica definitiva é prerrogativa exclusiva da pesquisadora, que utilizará a amostra cega gerada para cálculo de concordância interanotador (*Cohen's Kappa*).

---

## 2. Arquivos de Entrada e Hashes SHA-256

1. **Fila de Evidências (619 registros):**
   - **Caminho absoluto:** `C:\MestradoEstudoRag\ragdiretrizes\dados_derivados\analysis\todos_paises_exploratorio_20260927_01\human_validation\evidence_review_queue.csv`
   - **SHA-256:** `1c84ef4e7648b88208b47e798dbf8c68b1d13354ca1c774acc1ae72cd1e0288b`
   - **Contém:** 619 evidências cobrindo 22 países e perguntas Q01 a Q13, associadas ao texto das páginas físicas extraídas dos PDFs (`dataset_text_at_cited_page`) e ao mapeamento de páginas alternativas no mesmo documento (`matching_pages_same_document`).

2. **Respostas Consolidadas (286 registros — 22 países × 13 perguntas):**
   - **Caminho absoluto:** `C:\MestradoEstudoRag\ragdiretrizes\dados_derivados\analysis\todos_paises_exploratorio_20260927_01\resultados_rag_q01_q13_avaliacao_1.xlsx` (aba `Respostas detalhadas`)
   - **SHA-256:** `e0d5acf08808a64299b7b4a0cf97889670a370715f81afbd73a1deaeae5a24a0`
   - **Contém:** Todas as 286 respostas do sistema RAG, incluindo as 20 respostas marcadas como `inconclusive` na rodada preliminar por insuficiência de recuperação.

---

## 3. Regras Metodológicas Aplicadas

### 3.1 Regras Determinísticas Pré-Juiz (sem chamada à API)
1. **Páginas sem texto:** As 14 evidências com `citation_audit_result = cited_page_missing` receberam diretamente o status `inconclusive` com a justificativa: *"sem texto de página disponível para verificação."*
2. **China (OCR ilegível):** As 22 evidências da China receberam diretamente o status `inconclusive` com a justificativa: *"texto da página ilegível (OCR); documento apenas em imagem."*
3. **Respostas RAG inconclusivas na origem:** As respostas marcadas como `inconclusive` na geração RAG receberam diretamente o status `inconclusive` com a justificativa: *"Resposta RAG inconclusiva de origem por insuficiência de recuperação documental preliminar no corpus do país."*

### 3.2 Avaliação Contextual e Não Circular
- O modelo recebeu obrigatoriamente o **texto real da página física do documento curricular** (`dataset_text_at_cited_page`). Quando o trecho não estava na página citada, o sistema carregou e forneceu também o texto das páginas de `matching_pages_same_document` do cache original dos PDFs.
- **Nenhuma evidência foi sugerida como `validated` sem uma página física comprovada:** quando o apoio não foi encontrado em nenhuma página do documento, o status foi forçado para `rejected` ou `inconclusive`. Para cada evidência validada ou reformulada, foram gravadas as colunas `llm_supporting_page`, `corrected_page_start` e `corrected_source_text`.

### 3.3 Condicionamento das Respostas às Evidências
- Uma resposta do RAG só pôde ser sugerida como `validated` se suas afirmações principais estivessem amparadas em evidências pré-classificadas como `validated` ou `reformulated`.
- Quando nenhuma evidência associada à resposta sustentava o conteúdo, a resposta foi classificada como `rejected` ou `inconclusive`.
- A justificativa da resposta (`llm_justification`) lista explicitamente os `evidence_id` que fornecem apoio.

### 3.4 Revisão de Autoria (`authorship_review`)
- Foram sinalizados na coluna `authorship_review` como `em_revisao` todos os registros vinculados aos documentos:
  - `BR_007`: Fundação Telefônica Vivo
  - `BR_011`: CIEB
  - `BR_014`: Parecer CNE/CP 7/2022 (fora do tema curricular direto)
  - `US_001`: K-12 CS Framework (orientador não mandatório)
- Os demais documentos foram rotulados como `regular`.

---

## 4. Totais Consolidados (Gerados por Script Reprodutível)

Script de conferência disponível no repositório: `python scripts/contagem_preclassificacao.py`.

### 4.1 Evidências (619 registros)

#### Total Geral
| Status Sugerido pelo Modelo | Qtd | % |
|---|---:|---:|
| `validated` | 440 | 71,1% |
| `reformulated` | 67 | 10,8% |
| `rejected` | 74 | 12,0% |
| `inconclusive` | 38 | 6,1% |
| **Total** | **619** | **100,0%** |

#### Recorte por Revisão de Autoria
- **Documentos em revisão (`em_revisao`):** 39 evidências.
- **Documentos oficiais sem revisão (`regular`):** 580 evidências.

| Status Sugerido | Corpus sem documentos em revisão (`regular`) | Apenas documentos em revisão (`em_revisao`) | Total Geral |
|---|---:|---:|---:|
| `validated` | 411 | 29 | 440 |
| `reformulated` | 65 | 2 | 67 |
| `rejected` | 66 | 8 | 74 |
| `inconclusive` | 38 | 0 | 38 |
| **Total** | **580** | **39** | **619** |

#### Distribuição das Evidências por Pergunta (Q01 a Q13)
| Pergunta | Validated | Reformulated | Rejected | Inconclusive | Total |
|---|---:|---:|---:|---:|---:|
| Q01 | 35 | 5 | 6 | 1 | 47 |
| Q02 | 30 | 2 | 7 | 4 | 43 |
| Q03 | 34 | 8 | 7 | 3 | 52 |
| Q04 | 36 | 3 | 3 | 3 | 45 |
| Q05 | 36 | 2 | 3 | 4 | 45 |
| Q06 | 41 | 2 | 2 | 2 | 47 |
| Q07 | 34 | 5 | 9 | 2 | 50 |
| Q08 | 26 | 10 | 9 | 3 | 48 |
| Q09 | 29 | 7 | 3 | 3 | 42 |
| Q10 | 31 | 8 | 8 | 2 | 49 |
| Q11 | 39 | 4 | 7 | 2 | 52 |
| Q12 | 27 | 11 | 5 | 4 | 47 |
| Q13 | 42 | 0 | 5 | 5 | 52 |

---

### 4.2 Respostas RAG (286 registros: 22 países × 13 perguntas)

#### Total Geral
| Status Sugerido pelo Modelo | Qtd | % |
|---|---:|---:|
| `validated` | 182 | 63,6% |
| `reformulated` | 54 | 18,9% |
| `rejected` | 30 | 10,5% |
| `inconclusive` | 20 | 7,0% |
| **Total** | **286** | **100,0%** |

#### Distribuição das Respostas por Pergunta (Q01 a Q13)
| Pergunta | Validated | Reformulated | Rejected | Inconclusive | Total |
|---|---:|---:|---:|---:|---:|
| Q01 | 13 | 5 | 2 | 2 | 22 |
| Q02 | 14 | 4 | 2 | 2 | 22 |
| Q03 | 12 | 6 | 3 | 1 | 22 |
| Q04 | 14 | 6 | 1 | 1 | 22 |
| Q05 | 20 | 0 | 2 | 0 | 22 |
| Q06 | 18 | 2 | 1 | 1 | 22 |
| Q07 | 12 | 5 | 4 | 1 | 22 |
| Q08 | 9 | 9 | 2 | 2 | 22 |
| Q09 | 15 | 3 | 1 | 3 | 22 |
| Q10 | 12 | 6 | 2 | 2 | 22 |
| Q11 | 15 | 1 | 3 | 3 | 22 |
| Q12 | 10 | 7 | 4 | 1 | 22 |
| Q13 | 18 | 0 | 3 | 1 | 22 |

---

## 5. Artefatos Gerados e Hashes SHA-256

Todos os arquivos estão localizados em `dados_derivados/analysis/todos_paises_exploratorio_20260927_01/human_validation/`:

1. **`classificacao_evidencias_auditadas.csv`** (619 linhas)
   - **SHA-256:** `a77a8b6fbd8be9354172125fd605d57dc408fca37ddec0442b4864c1186f8b5b`
   - **Colunas:** `evidence_id`, `question_id`, `country`, `document_id`, `authorship_review`, `llm_suggested_status`, `llm_supporting_page`, `corrected_page_start`, `corrected_source_text`, `llm_justification`, `llm_reviewed_at`, `model_snapshot`.

2. **`classificacao_respostas_auditadas.csv`** (286 linhas)
   - **SHA-256:** `9cfab32da1413786e97243ad98c7c9f04bf6807d2ad9bfcac5fd61193df1c2b3`
   - **Colunas:** `country`, `country_name`, `question_id`, `question_text`, `llm_suggested_status`, `llm_supporting_evidence_ids`, `llm_justification`, `llm_reviewed_at`, `model_snapshot`.

3. **`amostra_conferencia_humana.csv`** (50 linhas sorteadas, semente `seed=42`)
   - **SHA-256 após a conferência humana:** `1d1a5b1ffb773fa7f0f29f627ce9b8767852aa6fe3d79d5262fb1dd1e08e9431`
   - **Colunas:** `evidence_id`, `country`, `question_id`, `rag_source_text`, `dataset_text_at_cited_page`, `minha_decisao`. A amostra foi entregue totalmente às cegas, sem status nem justificativa do modelo.
   - **Conferência humana (13/10/2026):** a pesquisadora conferiu a página indicada para as 50 evidências sem consultar o gabarito do modelo. Foram classificadas 16 evidências como `validated` (32%), 15 como `reformulated` (30%), 17 como `rejected` (34%) e 2 como `inconclusive` (4%). `reformulated` indica apoio documental com necessidade de ajustar página, contexto, tradução ou redação; `rejected` indica que a página não sustenta a resposta; e `inconclusive` indica que a verificação não foi possível.
   - **Confronto posterior com o gabarito:** houve concordância em 21 das 50 classificações (42,0%). Considerando as quatro categorias, o coeficiente kappa de Cohen foi `0,162`, o que evidencia baixa concordância entre a pré-classificação do modelo e a conferência humana. A amostra não valida automaticamente as demais evidências da rodada; elas continuam sujeitas à revisão humana.

4. **`amostra_gabarito_modelo.csv`** (50 linhas correspondentes ao gabarito)
   - **SHA-256:** `7ebb6994f8e03ecc274737edad1ad418377d06eba416ef2a96e552399faa5a2f`
   - **Colunas:** `evidence_id`, `country`, `question_id`, `llm_suggested_status`, `llm_supporting_page`, `llm_justification`.

5. **`metadados_execucao_classificacao.json`**
   - Registro estruturado completo dos metadados de execução, parâmetros e integridade criptográfica de cada arquivo.
