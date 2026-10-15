# Protocolo de validação humana para alimentar a Q14

## Objetivo

Esta camada separa a geração automática do RAG da interpretação científica final. As respostas Q01-Q13 e as comparações automáticas podem sugerir padrões, diferenças e lacunas, mas a Q14 final deve ser construída somente a partir de achados validados ou reformulados pela pesquisadora.

## Arquivo principal

A validação humana é registrada em:

```text
analysis/official_run_20260912/human_validation/validated_findings.csv
```

O arquivo é criado por:

```bash
python -m rag_project.init_human_validation
```

## Campos

- `finding_id`: identificador único e estável do achado.
- `question_id`: Q01 a Q13.
- `country`: país relacionado; pode ficar vazio para achado transversal.
- `finding_type`: `convergence`, `difference`, `recurring_pattern`, `evidence_gap` ou `country_finding`.
- `finding_source`: origem do achado, por exemplo `model_comparison`, `researcher_observation` ou `new_evidence`.
- `original_claim`: redação original sugerida pelo modelo, quando houver.
- `curated_claim`: redação aprovada pela pesquisadora.
- `evidence_ids`: IDs das evidências que sustentam o achado, separados por `;`.
- `document_ids`: documentos associados, separados por `;`.
- `pages`: páginas associadas.
- `validation_status`: `validated`, `reformulated` ou `rejected`.
- `validator_notes`: justificativa da decisão humana.
- `validated_at`: data da validação.

## Regras de uso

### 1. Quando a pesquisadora confirma o achado do RAG

Use:

```text
validation_status = validated
```

Preserve a ideia no campo `curated_claim` e registre os IDs de evidência que sustentam a interpretação.

### 2. Quando a ideia é pertinente, mas a redação do modelo extrapola

Use:

```text
validation_status = reformulated
```

Mantenha a formulação original em `original_claim` e registre a versão científica corrigida em `curated_claim`.

Exemplo: se o modelo disser "a maioria dos países" mas os países listados não representam a maioria do corpus, a redação pode ser reformulada para "em alguns países" ou "nas evidências recuperadas para os países listados".

### 3. Quando o achado deve ser descartado

Use:

```text
validation_status = rejected
```

Explique o motivo em `validator_notes`. Achados rejeitados nunca entram na Q14 validada.

### 4. Quando a pesquisadora identifica algo novo já sustentado pelas evidências recuperadas

Use:

```text
finding_source = researcher_observation
```

Crie um novo `finding_id`, registre o `question_id`, a redação em `curated_claim` e associe as evidências/documentos/páginas existentes.

### 5. Quando a pesquisadora identifica algo no documento que o RAG não recuperou

Não inserir diretamente como conclusão comparativa. Primeiro é necessário registrar a nova evidência com documento, página e trecho original. Depois o achado pode entrar no arquivo de validação com:

```text
finding_source = new_evidence
```

A rastreabilidade deve ser preservada.

## Geração da entrada validada para Q14

Depois da revisão humana:

```bash
python -m rag_project.build_q14_validated_input
```

Esse comando gera:

```text
analysis/official_run_20260912/comparison/q14_validated_input.csv
analysis/official_run_20260912/comparison/q14_validated_input_audit.json
```

Somente linhas com `validation_status` igual a `validated` ou `reformulated` entram na base da Q14.

## Execução da Q14 validada

Quando a validação das Q01-Q13 estiver concluída:

```bash
python -m rag_project.run_q14_validated
```

A saída será:

```text
analysis/official_run_20260912/comparison/q14_validated_final.json
```

A Q14 validada usa exclusivamente os achados aprovados pela pesquisadora. Ela não consulta novamente o corpus bruto e não utiliza achados rejeitados.

## Princípios metodológicos

1. Ausência de recuperação não equivale a ausência conceitual.
2. `inconclusive` indica insuficiência de evidência, não inexistência do conceito.
3. A análise documental não mede implementação, impacto ou efetividade.
4. Toda síntese comparativa deve ser rastreável a perguntas e achados validados.
5. Interpretação humana e registro da decisão são parte explícita do método.
6. O histórico automático não deve ser apagado; a validação humana constitui uma nova camada de curadoria.

## Fluxo final

```text
Corpus oficial
  ↓
RAG por país (Q01-Q13)
  ↓
Evidências e respostas candidatas
  ↓
Comparações automáticas por pergunta
  ↓
Validação humana
  ↓
validated_findings.csv
  ↓
q14_validated_input.csv
  ↓
Q14 validada
  ↓
Quadros, análise e redação da dissertação
```
