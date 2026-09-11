# Primeira rodada do RAG

Este diretório documenta e organiza a primeira rodada reprodutível da análise RAG por país.

## Objetivo

Executar as perguntas estruturadas do catálogo ativo por país, usando o OpenAI Vector Store para evitar o carregamento local do FAISS e do modelo de embeddings.

A rodada deve produzir:

- um dataset documental baseado no registro oficial;
- um Vector Store novo, sem reaproveitar o índice antigo;
- respostas individuais por país;
- evidências com documento, página, trecho, classificação e estado de validação;
- o arquivo agregado `02_perguntas_respostas.xlsx`.

## Estado de controle

- Versão do corpus: `3.0`
- Versão das perguntas: `2.0`
- Países ativos: `22`
- Referências externas: UNESCO e PISA/OCDE, não são países
- País excluído: Marrocos
- Perguntas estruturadas atuais: `Q01`, `Q06`, `Q16`, `Q18`, `Q22`
- Perguntas executadas nesta primeira rodada por país: `Q01`, `Q06` e `Q22`
- Backend recomendado: OpenAI Vector Store

## 1. Ativar o ambiente

No Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

No Git Bash:

```bash
source .venv/Scripts/activate
```

Verifique as dependências:

```bash
pip install -r rag_project/requirements.txt
```

A chave deve estar em `rag_project/.env`:

```text
OPENAI_API_KEY=...
```

Não registre a chave em arquivos, logs ou commits.

## 2. Conferir o registro do corpus

O arquivo oficial é:

```text
rag_project/config/corpus_registry.yaml
```

Verifique:

```bash
python -c "import yaml; from pathlib import Path; p=Path('rag_project/config/corpus_registry.yaml'); d=yaml.safe_load(p.read_text(encoding='utf-8')); print('versao:', d['corpus_version']); print('paises:', d['total_countries']); print('ativos:', sum(c.get('include_in_analysis', False) for c in d['countries'])); print('excluidos:', [c['country'] for c in d.get('excluded_countries', [])])"
```

Regras obrigatórias:

- somente documentos listados no registro entram no dataset;
- `include_in_analysis` deve ser `true`;
- documentos `rejected` não entram;
- somente papéis `primary` e `complementary` entram;
- Marrocos permanece explicitamente excluído;
- UNESCO e PISA/OCDE ficam em `benchmark_sources`, fora da contagem de países.

Antes da execução, conferir se os quatro arquivos de China e Estônia existem com nomes minúsculos:

```bash
python -c "from pathlib import Path; files=['corpus/china/china_information_technology_curriculum_standard_2022.pdf','corpus/china/china_compulsory_education_curriculum_plan_2022.pdf','corpus/estonia/estonia_national_curriculum_basic_schools_2026.pdf','corpus/estonia/estonia_informatics_appendix_10_2023.pdf']; print(*[f'{p}: {Path(p).exists()}' for p in files], sep='\n')"
```

## 3. Reconstruir os datasets

Não usar o dataset antigo como fonte da rodada. Remover ou mover previamente os arquivos antigos para `historico-versoes` se necessário.

Executar sem tradução automática na primeira rodada:

```bash
python -m rag_project.build_dataset --corpus corpus --out corpus/dataset_output
```

Conferir a quantidade de registros:

```bash
python -c "from pathlib import Path; import json; p=Path('corpus/dataset_output/dataset_original.jsonl'); rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]; print('registros:', len(rows)); print('paises:', sorted(set(r.get('country','') for r in rows))); print('marrocos:', any(r.get('country') == 'marrocos' for r in rows))"
```

Critério de aprovação:

- `marrocos: False`;
- todos os registros devem possuir `corpus_version: 3.0`;
- cada registro deve possuir `document_id`;
- China e Estônia devem aparecer quando seus arquivos estiverem registrados e legíveis.

## 4. Criar um Vector Store novo

Não reutilizar os IDs antigos `vs_6a923b92f4648191931249924f74f303` ou `vs_6a923591310c8191b7b465ec6f891515` para a rodada v3.0.

Enviar o dataset original ou inglês recém-gerado:

```bash
python rag_project/openai_vector_store.py upload \
  --file corpus/dataset_output/dataset_original.jsonl \
  --name ragdiretrizes-corpus-v3.0-questions-v2.0
```

Guardar o novo `vector_store_id` em local seguro. Não colocar a chave no arquivo.

Recomenda-se registrar o ID no manifesto de execução, junto com:

```text
corpus_version=3.0
question_version=2.0
backend=openai
vector_store_id=...
```

## 5. Executar a rodada por país

A execução padrão grava em `analysis/countries/<pais>/respostas.csv`.

Exemplo para China:

```bash
python rag_project/run_questions_by_country.py \
  --country china \
  --backend openai \
  --vector_store_id SEU_VECTOR_STORE_V3 \
  --openai_key SUA_CHAVE
```

Exemplo para Estônia:

```bash
python rag_project/run_questions_by_country.py \
  --country estonia \
  --backend openai \
  --vector_store_id SEU_VECTOR_STORE_V3 \
  --openai_key SUA_CHAVE
```

Para executar todos os países ativos no PowerShell:

```powershell
$countryNames = @('africa-do-sul','australia','brasil','canada','chile','china','coreia-do-sul','estonia','eua','finlandia','gana','hong-kong','irlanda','japao','nova-zelandia','quenia','reino-unido','ruanda','singapura','suica','taiwan','uruguai')
foreach ($country in $countryNames) {
  python rag_project/run_questions_by_country.py --country $country --backend openai --vector_store_id SEU_VECTOR_STORE_V3 --openai_key $env:OPENAI_API_KEY
}
```

Para cada país, conferir:

```text
analysis/countries/<pais>/respostas.csv
analysis/countries/<pais>/question_run_log.csv
```

País sem documentos registrados deve permanecer sem evidência, com estado `candidate` ou `not_detected`; não preencher manualmente a resposta.

## 6. Validar as evidências

Cada resposta deve ser conferida contra o documento original. Para cada evidência, validar:

- `question_id`;
- país e código do país;
- `document_id`;
- nome do documento;
- página inicial e final;
- trecho original;
- classificação: explícita, implícita, não detectada ou inconclusiva;
- `validation_status`;
- limitações do OCR, especialmente nos documentos chineses.

China somente deve ser marcada como `validated` depois da conferência do OCR com a página original.

## 7. Gerar o workbook agregado

Depois da validação individual:

```bash
python rag_project/build_question_answer_workbook.py \
  --input analysis/countries \
  --out analysis/02_perguntas_respostas.xlsx
```

Abas esperadas:

```text
00_dicionario
01_respostas_longas
02_<pais> ... 23_<pais>
24_matriz_agregada
25_controle_validacao
```

UNESCO e PISA/OCDE não devem receber abas de país. Eles são referências internacionais.

## 8. Checklist de encerramento

- [ ] Dataset reconstruído a partir do registro v3.0
- [ ] Marrocos não aparece no dataset ativo
- [ ] China e Estônia conferidas
- [ ] Novo Vector Store criado
- [ ] ID do Vector Store registrado fora do código
- [ ] Cache antigo não reutilizado
- [ ] Respostas geradas por país
- [ ] Evidências humanas validadas
- [ ] `02_perguntas_respostas.xlsx` gerado
- [ ] UNESCO e PISA/OCDE mantidos como referências, não países
- [ ] Testes executados: `python -m pytest -q`
- [ ] `git diff --check` executado antes do commit

## Observação importante

O catálogo atual contém 22 países, mas o registro deve possuir documentos ativos para cada país antes de uma rodada completa. Países com `documents: []` ainda não têm base documental registrada para responder legitimamente às perguntas.
