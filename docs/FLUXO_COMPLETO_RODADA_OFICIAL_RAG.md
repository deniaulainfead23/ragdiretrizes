# Fluxo completo da rodada oficial do RAG

## 1. Objetivo deste documento

Este documento registra, de forma cronológica e reprodutível, o fluxo executado para preparar o corpus, validar os documentos, construir o dataset de conteúdo, indexar o corpus, executar as perguntas analíticas por país, reparar inconsistências, auditar os resultados e gerar a etapa comparativa Q14.

A rodada descrita corresponde ao diretório:

```text
analysis/official_run_20260912
```

O objetivo metodológico foi preservar rastreabilidade entre pergunta, resposta, evidência, documento e página, evitando transformar ausência de recuperação em ausência conceitual.

---

## 2. Escopo do corpus

O corpus nacional considerado na rodada oficial possui 22 países:

```text
africa-do-sul
australia
brasil
canada
chile
china
coreia-do-sul
estonia
eua
finlandia
gana
hong-kong
irlanda
japao
nova-zelandia
quenia
reino-unido
ruanda
singapura
suica
taiwan
uruguai
```

UNESCO e OECD/PISA são tratados como referências internacionais e não entram na contagem dos 22 países.

O catálogo mestre do corpus é:

```text
metadata/documentos.csv
```

O manifesto de processamento é:

```text
metadata/processed_documents.csv
```

Na auditoria final do corpus foram registrados 86 documentos, distribuídos em grupos de qualidade textual e processamento.

---

## 3. Auditoria e preparação textual

O fluxo aplicado aos documentos foi:

```text
inventário
→ auditoria de metadados
→ extração direta
→ avaliação por página
→ OCR seletivo nas exceções
→ revisão das páginas problemáticas
→ registro da decisão
→ validação do dataset
→ liberação para indexação
```

Princípios aplicados:

- preservar os documentos originais;
- manter `document_id` estável;
- preservar página de origem sempre que possível;
- não aplicar OCR de forma indiscriminada;
- usar OCR somente nos documentos/páginas bloqueados ou sem texto útil;
- registrar exceções estruturais em vez de descartá-las silenciosamente;
- tratar páginas vazias ou de baixa qualidade como gatilho de revisão, e não como exclusão automática.

Artefatos principais:

```text
OCR_Seletivo_Corpus_RAG.ipynb
Auditoria_Reutilizavel_Corpus_RAG.ipynb
rag_project/audit_corpus.py
docs/PROTOCOLO_VALIDACAO_TEXTOS.md
```

---

## 4. Exceções de OCR e revisão manual

Alguns documentos exigiram OCR seletivo. Entre os casos relevantes estiveram documentos chineses e um documento de Singapura.

No documento chinês AS-CN-02 foi necessária correção manual da página 6, referente ao sumário. A página 7 foi registrada como sem texto OCR útil. A correção foi realizada antes da indexação para impedir que a referência de página ficasse inconsistente no RAG.

O princípio adotado foi registrar explicitamente a intervenção humana, preservando a rastreabilidade.

---

## 5. Construção do dataset de conteúdo

O script principal de construção do dataset é:

```text
rag_project/build_content_dataset.py
```

A saída consolidada é:

```text
data/conteudos.jsonl
```

Os textos processados são segmentados por página e identificados por metadados de rastreabilidade.

Campos principais:

```text
content_id
chunk_id
document_id
country
source_scope
framework_source
document_title
year
language
page_start
page_end
source_text
char_count
token_estimate
audit_group
processing_status
source_path
processed_path
```

Na validação final do JSONL foram obtidos:

```text
Registros: 8099
Documentos únicos: 86
content_id únicos: 8099
Duplicados: 0
Textos vazios: 0
```

Foi corrigido também um problema de separadores Unicode U+2028/U+2029 que afetava a consistência do JSONL.

---

## 6. Indexação vetorial

Os 86 documentos processados foram enviados ao OpenAI Vector Store.

Vector Store oficial da rodada:

```text
vs_6aa4d08cc1948191bc425516c4087b85
```

O manifesto local utilizado pelo código é:

```text
rag_project/.openai_vector_stores.json
```

O backend OpenAI é o principal. O backend local permanece como alternativa/fallback.

A recuperação preserva atributos de país, documento, idioma e demais metadados necessários à rastreabilidade.

---

## 7. Perguntas analíticas Q01–Q14

O catálogo de perguntas está em:

```text
rag_project/questions/questions.yaml
```

As perguntas Q01–Q13 são perguntas de recuperação documental por país (`evidence_retrieval`).

A Q14 é uma pergunta de comparação internacional (`validated_comparison`).

A arquitetura metodológica definida foi:

```text
pergunta por país
→ recuperação de evidências
→ resposta nacional
→ auditoria/validação
→ consolidação comparativa
→ Q14
```

A Q14 não deve ser usada para substituir a recuperação por país.

---

## 8. Execução oficial Q01–Q13

Diretório da rodada:

```text
analysis/official_run_20260912
```

Para cada país foram produzidos arquivos de resposta e evidência, incluindo:

```text
respostas.csv
evidencias.csv
question_run_log.csv
```

A rastreabilidade segue a lógica:

```text
run_id
→ question_run_id
→ question_id
→ response_id
→ evidence_id
→ document_id
→ page_start/page_end
```

A execução oficial produziu todas as combinações esperadas:

```text
22 países × 13 perguntas = 286 respostas
```

---

## 9. Problemas encontrados após a primeira execução

A primeira auditoria detectou problemas de dois tipos:

1. evidências com documento conhecido, mas página ausente;
2. respostas em que o modelo devolveu JSON ou quase-JSON dentro do campo textual, dificultando a consolidação das evidências.

Casos relevantes envolveram Brasil, Canadá, China e Estônia.

Também houve respostas realmente inconclusivas, que não deveriam ser tratadas como erro estrutural.

---

## 10. Reparação da rodada oficial

Foi criado o script:

```text
rag_project/repair_official_run.py
```

O script:

- cria backup antes das alterações;
- localiza evidências no dataset `data/conteudos.jsonl`;
- tenta recuperação por correspondência exata normalizada;
- usa âncoras de início/fim quando necessário;
- aplica fuzzy matching de forma conservadora;
- recupera evidências embutidas em respostas JSON/quase-JSON;
- tolera caracteres de controle inválidos e formatos próximos de literais Python;
- registra todas as ações em `repair_log.csv`.

Métodos de localização usados:

```text
exact_normalized
anchors_range
anchor_start
anchor_end
fuzzy conservador
```

---

## 11. Correções relevantes da reparação

### Brasil

Foram recuperadas páginas ausentes em diferentes perguntas.

Um caso importante ocorreu em Q05: uma evidência havia sido atribuída ao documento `BR_007`, mas a busca no dataset consolidado mostrou que o trecho pertencia ao documento `BR_005`, página 5. A evidência foi reassociada ao documento correto para preservar a rastreabilidade.

### Canadá Q03

A resposta continha evidências embutidas em JSON, mas elas não haviam sido estruturadas em `evidencias.csv`. O script recuperou três evidências e a resposta deixou de ser um falso caso sem evidência.

### China Q02

A resposta continha JSON malformado com caracteres de controle. O parser do script de reparação foi ajustado para recuperar as duas evidências presentes no conteúdo.

### Estônia

Páginas ausentes foram localizadas no dataset consolidado utilizando correspondência exata e âncoras textuais.

---

## 12. Resultados inconclusivos

Ao final da reparação permaneceram três respostas `inconclusive`.

Dois casos não possuíam evidência recuperada suficiente e um caso possuía evidências, mas ainda assim foi considerado insuficiente para uma resposta afirmativa.

Regra metodológica:

> `inconclusive` significa insuficiência de evidência recuperada para responder à pergunta. Não significa que o conceito esteja ausente no currículo, no documento ou no país.

---

## 13. Auditoria estrutural final Q01–Q13

A auditoria final produziu:

```text
Países: 22
Respostas: 286
Esperado: 286
Candidates: 283
Inconclusive: 3
Evidências: 626
Problemas estruturais: 0

AUDITORIA ESTRUTURAL FINAL: OK
```

Esse resultado fecha a camada técnica das respostas Q01–Q13.

---

## 14. Construção da base comparativa Q14

Foi criado o script local:

```text
rag_project/build_q14_input.py
```

A saída é:

```text
analysis/official_run_20260912/comparison/q14_input.csv
```

Resultado:

```text
Linhas: 286
Países: 22
Perguntas: 13
Candidates: 283
Inconclusive: 3
Problemas: 0
```

A base Q14 reúne as respostas nacionais já produzidas, sem fazer nova recuperação no corpus bruto.

---

## 15. Comparações temáticas Q01–Q13

Foi criado o script:

```text
rag_project/run_q14_comparison.py
```

Ele produz uma comparação por pergunta e grava:

```text
analysis/official_run_20260912/comparison/q14_by_question.csv
```

Foram geradas 13 comparações temáticas, uma para cada pergunta Q01–Q13.

A síntese global foi inicialmente produzida em:

```text
q14_final.json
q14_final_v2.json
q14_final_v3.json
```

As versões posteriores introduziram regras mais rígidas para evitar ranking, interpretações de ausência, categorias fora de escopo e afirmações sobre efetividade/implementação não sustentadas por análise documental.

---

## 16. Aprendizado metodológico da Q14

A geração automática da comparação revelou um ponto importante: mesmo com o pipeline tecnicamente correto, uma síntese comparativa pode associar uma afirmação à pergunta-fonte errada ou extrapolar o escopo da evidência.

Exemplos observados durante a revisão:

- uso de Q10 para afirmações que pertenciam a Q06;
- criação de lacunas sobre avaliação do Pensamento Computacional, embora Q02 não perguntasse sobre avaliação;
- criação de lacunas sobre cidadania digital usando Q05;
- uso de expressões de intensidade ou comparação sem critério operacional;
- criação de categoria regional não prevista na análise;
- uso indevido de `kenia` em vez do identificador oficial `quenia`.

Por isso, a Q14 deve ser interpretada como saída computacional sujeita a curadoria semântica antes de uso no texto acadêmico final.

---

## 17. Fechamento técnico da rodada oficial

Foi criado um script local de fechamento:

```text
rag_project/finalize_official_run.py
```

Resultado final:

```text
=== FECHAMENTO DO PIPELINE ===
Países: 22
Respostas: 286
Esperado: 286
Candidates: 283
Inconclusive: 3
Evidências: 626
Q14 input: 286
Q14 temáticas: 13
Q14 final válido: True
Problemas: 0

PIPELINE OFICIAL FECHADO: OK
```

O manifesto produzido é:

```text
analysis/official_run_20260912/FINAL_RUN_MANIFEST.json
```

---

## 18. Comando único para preparar a rodada de análise

Foi adicionado ao repositório:

```text
rag_project/export_analysis_round.py
```

Execução:

```bash
python -m rag_project.export_analysis_round
```

Esse comando lê automaticamente todos os 22 países e as perguntas Q01–Q13 e gera:

```text
analysis/official_run_20260912/review_exports/questions/Q01.csv
...
analysis/official_run_20260912/review_exports/questions/Q13.csv

analysis/official_run_20260912/review_exports/countries/brasil.csv
...
analysis/official_run_20260912/review_exports/countries/uruguai.csv

analysis/official_run_20260912/review_exports/ANALYSIS_ROUND_MANIFEST.json
```

Assim, a etapa de análise não exige mais copiar e colar comandos para cada pergunta e país.

---

## 19. Próxima etapa metodológica

Após o fechamento técnico, a pesquisa entra na fase de análise científica.

A sequência recomendada é:

```text
Q01 → análise dos 22 países
Q02 → análise dos 22 países
...
Q13 → análise dos 22 países
→ revisão das evidências quando necessário
→ consolidação dos padrões por pergunta
→ síntese comparativa Q14 curada
→ quadros e tabelas
→ redação do capítulo de resultados
```

Para cada pergunta, recomenda-se registrar:

- convergências;
- diferenças de formulação e organização;
- padrões recorrentes;
- lacunas de evidência recuperada;
- respostas inconclusivas;
- países/documentos/evidências que sustentam cada afirmação;
- observações metodológicas.

---

## 20. Regras que não devem ser quebradas na análise

1. Ausência de recuperação não equivale a ausência conceitual.
2. `inconclusive` não equivale a inexistência do tema no país.
3. O estudo documental não mede implementação, efetividade ou impacto em sala de aula.
4. Não devem ser criados rankings de países sem desenho metodológico específico para isso.
5. Cada afirmação comparativa deve ser rastreável às perguntas e evidências nacionais.
6. Diferenças na quantidade e no tipo de documentos por país precisam aparecer nas limitações.
7. Tradução, OCR e recuperação semântica são mediações metodológicas e devem ser explicitadas.
8. A etapa automática não substitui a validação e interpretação crítica do pesquisador.

---

## 21. Arquivos-chave para reprodução

```text
metadata/documentos.csv
metadata/processed_documents.csv
data/conteudos.jsonl
rag_project/questions/questions.yaml
rag_project/openai_vector_store.py
rag_project/run_questions_by_country.py
rag_project/repair_official_run.py
rag_project/build_q14_input.py
rag_project/run_q14_comparison.py
rag_project/finalize_official_run.py
rag_project/export_analysis_round.py
analysis/official_run_20260912/
```

Nem todos os artefatos de execução precisam ser versionados, especialmente arquivos derivados grandes. O repositório deve preservar os scripts, protocolos, metadados e manifestos necessários para repetir o processo.

---

## 22. Estado da rodada

**Rodada oficial 20260912: tecnicamente fechada.**

O estágio atual é análise e validação científica das respostas já produzidas, e não nova geração de respostas.
