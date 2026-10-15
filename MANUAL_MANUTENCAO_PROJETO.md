# Manual de manutenção do projeto RAG Diretrizes

## 1. Como atualizar o GitHub

### 1.1 Verificar o estado do repositório

```bash
cd /c/MestradoEstudoRag/ragdiretrizes
git status
git branch
```

### 1.2 Adicionar arquivos modificados

```bash
git add .
```

### 1.3 Criar um commit

```bash
git commit -m "Atualiza pipeline, documentação e RAG"
```

### 1.4 Subir para o GitHub

```bash
git push origin main
```

Se a branch for diferente, use:

```bash
git push origin <nome-da-branch>
```

### 1.5 Verificar se o repositório está limpo

```bash
git status
```

> Se aparecer arquivos não rastreados, verifique se há itens sensíveis (.env, dados locais, caches) antes de fazer o push.

---

## 2. Como limpar o cache

O projeto usa cache para respostas do RAG em:

- `rag_project/.cache/openai_cache.json`

### 2.1 Limpar o cache completo

```bash
cd /c/MestradoEstudoRag/ragdiretrizes
rm -rf rag_project/.cache
mkdir -p rag_project/.cache
```

No Windows PowerShell:

```powershell
cd C:\MestradoEstudoRag\ragdiretrizes
Remove-Item -Recurse -Force .\rag_project\.cache
New-Item -ItemType Directory -Path .\rag_project\.cache | Out-Null
```

### 2.2 Verificar se o cache foi apagado

```bash
ls rag_project/.cache
```

### 2.3 Quando limpar o cache

- quando quiser testar uma pergunta nova sem reaproveitar resposta antiga;
- quando houver mudança na base documental;
- quando quiser forçar nova recuperação no Vector Store;
- quando o conteúdo do projeto foi atualizado e a resposta em cache ficou desatualizada.

---

## 3. Como fazer perguntas para o RAG

### 3.0 Mensagens de progresso no RAG

O projeto agora exibe mensagens de status para ajudar a acompanhar a execução real da consulta:

```text
[0/4] Inicializando consulta...
[0/4] Backend selecionado: openai
[1/4] Usando backend OpenAI Vector Store...
[2/4] Buscando documentos no Vector Store ...
[3/4] Encontrados trechos relevantes para a consulta.
[4/4] Gerando resposta...
```

Essas mensagens são importantes porque a primeira consulta costuma ser mais lenta. Isso acontece por dois motivos principais:

1. o índice vetorial ou o Vector Store ainda está sendo carregado;
2. a recuperação semântica precisa consultar vários documentos e embeddings em conjunto.

Depois que o índice está quente em memória, as consultas seguintes normalmente ficam muito mais rápidas. Se a primeira pergunta demorar vários minutos, isso pode ser normal em um corpus grande; se a segunda e as seguintes também demorarem de forma persistente, vale investigar se o backend está travado, se a chave OpenAI está válida ou se há problema na conexão.

### 3.1 Comando base

```bash
cd /c/MestradoEstudoRag/ragdiretrizes
PYTHONPATH="$PWD:$PWD/rag_project" python rag_project/run_query.py \
  --vector_store_id vs_6a923591310c8191b7b465ec6f891515 \
  --question "Sua pergunta aqui"
```

### 3.2 Exemplos de perguntas

#### Perguntas por país

```bash
PYTHONPATH="$PWD:$PWD/rag_project" python rag_project/run_query.py \
  --vector_store_id vs_6a923591310c8191b7b465ec6f891515 \
  --question "Como o Brasil define competências digitais em seus documentos curriculares?"
```

```bash
PYTHONPATH="$PWD:$PWD/rag_project" python rag_project/run_query.py \
  --vector_store_id vs_6a923591310c8191b7b465ec6f891515 \
  --question "Como a Finlândia trata a educação digital em seus currículos?"
```

#### Perguntas por tema

```bash
PYTHONPATH="$PWD:$PWD/rag_project" python rag_project/run_query.py \
  --vector_store_id vs_6a923591310c8191b7b465ec6f891515 \
  --question "Quais temas digitais aparecem com mais frequência nas diretrizes curriculares?"
```

```bash
PYTHONPATH="$PWD:$PWD/rag_project" python rag_project/run_query.py \
  --vector_store_id vs_6a923591310c8191b7b465ec6f891515 \
  --question "Como os currículos tratam pensamento crítico, ética digital e cidadania global?"
```

#### Perguntas de comparação

```bash
PYTHONPATH="$PWD:$PWD/rag_project" python rag_project/run_query.py \
  --vector_store_id vs_6a923591310c8191b7b465ec6f891515 \
  --question "Quais países apresentam maiores evidências de cidadania digital e pensamento crítico?"
```

```bash
PYTHONPATH="$PWD:$PWD/rag_project" python rag_project/run_query.py \
  --vector_store_id vs_6a923591310c8191b7b465ec6f891515 \
  --question "Há diferenças entre países com ênfase técnica e países com ênfase sociocultural na educação digital?"
```

### 3.3 Perguntas que devem ser evitadas

Evite perguntas que exigem ranking absoluto, como:

- "Qual país é o melhor?"
- "Quem está mais alinhado com a UNESCO?"
- "Qual currículo é superior?"

Essas perguntas não seguem a metodologia do projeto e podem produzir interpretações indevidas. Prefira perguntas focadas em evidência documental, tema, categoria e comparação metodológica.

---

## 4. Como rodar o projeto em ambiente local

### 4.1 Ativar o ambiente virtual

```bash
cd /c/MestradoEstudoRag/ragdiretrizes
source .venv/Scripts/activate
```

### 4.2 Rodar testes

```bash
python -m pytest -q
```

### 4.3 Rodar análise lexical

```bash
python rag_project/analyze_tfidf.py --input corpus/dataset_output/dataset_original.jsonl --out corpus/analysis_output --top-n 20
```

### 4.4 Rodar geração de gráficos

```bash
python rag_project/plot_csv_analysis.py --input corpus/analysis_output
```

---

## 5. Como manter o projeto em ordem

### Checklist recomendado

- revisar `git status` antes de commit;
- não subir `.env` com chaves reais;
- limpar cache quando houver alteração no corpus;
- manter perguntas no formato de evidência e não em ranking;
- manter documentos metodológicos atualizados;
- validar com `pytest` após mudanças relevantes.

---

## 6. Observações finais

Este projeto combina:

- análise documental;
- framework UNESCO;
- análise lexical exploratória;
- backend vetorial OpenAI;
- rastreabilidade por documento e evidência;
- recuperação semântica com RAG.

A regra central é: o RAG deve apoiar a leitura e a análise crítica, e não substituir a interpretação do pesquisador nem transformar similaridade textual em avaliação curricular.
