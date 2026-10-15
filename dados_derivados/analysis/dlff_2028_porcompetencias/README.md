# Análise lexical complementar por competências DLGF 2018

Este módulo é aditivo: não modifica scripts, dados ou resultados anteriores do projeto. Ele lê um JSONL existente em modo somente leitura, reúne registros de página por `document_id` e procura termos de um codebook com 26 competências. Cada documento completo é a unidade de análise. As páginas permanecem apenas para rastreabilidade.

## Requisitos

- Python 3.10 ou superior
- Bibliotecas padrão do Python; não requer instalação adicional

## Entradas esperadas

O JSONL precisa ter, em cada registro, `country`, `document_id` e o campo textual escolhido. O script padrão usa `english_text`, mas é obrigatório indicar `--text-field source_text` se a análise for feita no texto original. Quando o dataset contém várias páginas por documento, cada linha deve incluir `page_start` ou `page` para registrar as páginas em que os termos aparecem.

Para comparação lexical entre países, use a tradução em inglês integral e validada em um campo inglês. Não misture traduções incompletas ou o original de alguns países com traduções de outros. O script falha se o campo textual solicitado estiver ausente ou vazio.

## Execução

Na raiz do projeto:

```bash
python caminho/para/analyze_dlgf_competences.py \
  --input caminho/para/dataset_english.jsonl \
  --text-field english_text \
  --codebook caminho/para/unesco_dlgf_2018_competences.csv \
  --out dados_derivados/analysis/dlgf_competences/run_001 \
  --run-id run_001 \
  --source-revision SHA_DO_COMMIT_DO_PROJETO
```

A pasta de saída precisa ser nova. Isso evita sobrescrever qualquer rodada anterior.

## Saídas

- `document_competence_hits.csv`: uma linha por documento e competência, com termos encontrados, frequência, tamanho do documento, taxa por 10 mil palavras e páginas com ocorrência.
- `country_competence_summary.csv`: agregação por país e competência, incluindo número de documentos, cobertura documental, frequência absoluta e taxas normalizadas.
- `country_competence_matrix.csv`: países por competências; valores são percentuais de documentos do país com ao menos uma ocorrência lexical.
- `run_manifest.json`: hashes das entradas e saídas, versão do script, codebook, parâmetros, versões e contagens.

## Gráficos por país

Após concluir uma rodada, gere uma imagem PNG para cada país a partir do resumo:

```bash
python caminho/para/plot_country_competences.py \
  --input dados_derivados/analysis/dlff_2028_porcompetencias/run_001/country_competence_summary.csv \
  --out dados_derivados/analysis/dlff_2028_porcompetencias/run_001/imagens_por_pais
```

Cada gráfico apresenta a cobertura documental de cada uma das 26 competências específicas. As cores identificam as sete áreas gerais do DLGF (`CA0` a `CA6`). Os gráficos preservam a limitação metodológica da análise lexical.

O mapa de calor [country_competence_heatmap.png](./run_20261015_1033_english_validated/results/country_competence_heatmap.png) apresenta diretamente a mesma matriz país × competência, com escala fixa de 0 a 100% e o número de documentos de cada país. Ele é preferível a uma projeção t-SNE para a apresentação descritiva porque não cria eixos ou distâncias artificiais.

## Análise de proximidade — não utilizada

Foi gerada uma versão técnica de t-SNE, PCA, distâncias e agrupamento hierárquico na pasta `proximidade_paises/`, mas ela está **explicitamente excluída dos resultados e das interpretações da pesquisa**. A disposição dos pontos depende de padronização, métrica, perplexidade, semente e outros parâmetros, podendo fazer distâncias globais parecerem significativas.

Esses arquivos são mantidos somente para rastreabilidade da decisão metodológica. A análise final utiliza os CSVs de cobertura documental por país e competência, sem inferir agrupamentos ou proximidades globais.

## Interpretação e limitações

O codebook é uma versão inicial de termos indicadores em inglês derivados dos descritores DLGF. Antes de congelá-lo para a análise final, revise e versiona sinônimos, falsos positivos e variações terminológicas relevantes nos documentos do corpus. O script conta formas lexicais exatas, sem inferir equivalência semântica. Uma ocorrência não comprova que o currículo desenvolva a competência; zero ocorrências não comprova ausência conceitual. A saída não contém trechos de texto.

O DLGF mantém pensamento computacional (5.5) e programação (3.4) em códigos distintos. “Algorithm/algorithms” é indicador de busca para 5.5 e, por si só, não conta como programação em linguagem de código.

## FAIR e proveniência

O manifesto registra hashes, versão do código, identificador de rodada, parâmetros e contagens. CSV UTF-8 com BOM e IDs DLGF controlados facilitam interoperabilidade. Os PDFs oficiais permanecem fontes; direitos e condições de acesso devem ser preservados. FAIR não implica que arquivos protegidos devam ser publicados.
