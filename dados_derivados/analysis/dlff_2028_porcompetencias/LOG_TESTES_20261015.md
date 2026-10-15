# Log de testes e execução — DLGF por competências

**Data local:** 15/10/2026 10:20 (UTC-03:00)
**Data da execução registrada no manifesto:** 2026-10-15T13:02:36Z
**Pasta:** `dados_derivados/analysis/dlff_2028_porcompetencias`
**Rodada:** `run_20261015_0948`
**Revisão de origem:** `a4126d10bedd7074ec12bcf555b99261b27b6843`

## Processos executados

1. Compilação de sintaxe do script com Python 3.10.11:
   ```text
   C:\MestradoEstudoRag\ragdiretrizes\.venv\Scripts\python.exe -m py_compile dados_derivados\analysis\dlff_2028_porcompetencias\analyze_dlgf_competences.py
   ```
   **Resultado:** aprovado, sem erro de sintaxe.

2. Execução da análise lexical com a base original, usando explicitamente o campo `source_text`:
   ```text
   C:\MestradoEstudoRag\ragdiretrizes\.venv\Scripts\python.exe dados_derivados\analysis\dlff_2028_porcompetencias\analyze_dlgf_competences.py --input dados_intermediarios\data\conteudos.jsonl --text-field source_text --codebook dados_derivados\analysis\dlff_2028_porcompetencias\unesco_dlgf_2018_competences.csv --out dados_derivados\analysis\dlff_2028_porcompetencias\run_20261015_0948 --run-id dlff_2028_porcompetencias_20261015_0948 --source-revision a4126d10bedd7074ec12bcf555b99261b27b6843
   ```
   **Resultado:** concluído com sucesso.
   **Contagens:** 8.099 registros de entrada; 79 documentos; 22 países; 26 competências; 2.054 linhas documento-competência.

3. Validação automatizada de rastreabilidade:
   ```text
   C:\MestradoEstudoRag\ragdiretrizes\.venv\Scripts\python.exe -m pytest tests\test_dataset_traceability.py -q
   ```
   **Resultado:** 5 passed in 109.93s (0:01:49).

4. Diagnóstico do arquivo alterado pelo analisador.
   **Resultado:** nenhum erro reportado.

5. Conferência dos artefatos e do manifesto da rodada.
   **Resultado:** aprovados os quatro arquivos esperados:
   - `run_20261015_0948/document_competence_hits.csv`
   - `run_20261015_0948/country_competence_summary.csv`
   - `run_20261015_0948/country_competence_matrix.csv`
   - `run_20261015_0948/run_manifest.json`

6. Geração dos gráficos por país a partir de `country_competence_summary.csv`:
   ```text
   C:\MestradoEstudoRag\ragdiretrizes\.venv\Scripts\python.exe dados_derivados\analysis\dlff_2028_porcompetencias\plot_country_competences.py --input dados_derivados\analysis\dlff_2028_porcompetencias\run_20261015_0948\country_competence_summary.csv --out dados_derivados\analysis\dlff_2028_porcompetencias\run_20261015_0948\imagens_por_pais
   ```
   **Resultado:** 22 gráficos PNG gerados, um para cada país.
   **Validação:** compilação do script aprovada; os 22 PNGs foram abertos e validados; a imagem do Brasil foi inspecionada visualmente.

## Filtros e agregação observados

- 1.297 registros foram classificados como referências internacionais e excluídos da análise nacional.
- 6.802 registros elegíveis foram reunidos por `country + document_id`.
- A reunião das páginas produziu 79 documentos únicos; as páginas não foram tratadas como documentos independentes.
- O codebook contém 26 competências específicas distribuídas nas áreas gerais CA0 a CA6.
- Marrocos está configurado como país excluído pelo script, mas não houve registros de Marrocos nesta entrada.

## Rodada profissional — dataset inglês v2

Foi criada e concluída a rodada `run_20261015_1033_english_validated`.

**Status:** concluída e auditada.

- Dataset de entrada: 8.099 registros originais;
- Dataset inglês v2: 8.103 segmentos válidos;
- 5.113 segmentos traduzidos via OpenAI `gpt-4o-mini`;
- 2.990 registros já em inglês mantidos;
- `source_text` preservado e `english_text` usado na análise;
- 79 documentos, 22 países e 26 competências;
- 2.054 linhas documento–competência;
- 22 gráficos por país validados.
- 1 mapa de calor país × competência validado e escolhido como visualização descritiva principal.

A execução inicialmente apresentou uma falha transitória de DNS e depois uma correção de serialização JSONL para caracteres Unicode de separação de linha. O cache foi preservado e o dataset final foi regenerado e validado antes da análise. Os artefatos estão registrados em:

- `run_20261015_1033_english_validated/README.md`
- `run_20261015_1033_english_validated/AUDITORIA_PREVIA.md`
- `run_20261015_1033_english_validated/run_manifest.json`
- `run_20261015_1033_english_validated/input/dataset_english_v2.jsonl`
- `run_20261015_1033_english_validated/results/`
- `run_20261015_1033_english_validated/imagens_por_pais/`

## Proximidade entre países — excluída da análise final

Foi produzida uma análise técnica de t-SNE, PCA, distâncias euclidianas e agrupamento hierárquico sobre a matriz de cobertura. Após revisão metodológica, ela foi **excluída dos resultados e das interpretações finais** porque a configuração pode alterar a disposição dos países e fazer distâncias globais parecerem significativas.

Os artefatos permanecem em `run_20261015_1033_english_validated/proximidade_paises/` somente para rastreabilidade. A pesquisa não utilizará esses agrupamentos nem apresentará t-SNE como evidência de proximidade entre países.

O mapa de calor final, por apresentar diretamente percentuais de cobertura documental sem projeção de distâncias, está em `run_20261015_1033_english_validated/results/country_competence_heatmap.png`.

O fluxograma foi atualizado para representar corretamente a rodada final: `source_text` é preservado para proveniência e `english_text` é usado como campo analítico pelo codebook em inglês.

## Observação metodológica

As ocorrências produzidas são indicadores lexicais de busca. Não constituem validação semântica ou comprovação de que um currículo desenvolve determinada competência.
