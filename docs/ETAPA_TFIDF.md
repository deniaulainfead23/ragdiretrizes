# Etapa de TF-IDF e análise quantitativa

## 1. Objetivo

Esta etapa transforma o corpus curricular em indicadores quantitativos que apoiam a Educação Comparada. O objetivo não é substituir a leitura documental, mas identificar padrões lexicais, termos distintivos e proximidades textuais entre os países e o referencial UNESCO.

O processamento utiliza como entrada principal o dataset em inglês. O dataset original é preservado para rastreabilidade e conferência das traduções.

## 2. Entradas e unidade de análise

A entrada é o arquivo `corpus/dataset_output/dataset_english.jsonl`. Cada registro representa um documento e contém, entre outros campos:

- país ou grupo UNESCO;
- nome e caminho do documento;
- texto original;
- texto destinado à análise em inglês;
- grupo do dataset;
- indicador de referência UNESCO.

São utilizadas duas unidades de análise:

1. documento: permite identificar os termos mais relevantes de cada fonte;
2. grupo: agrega os documentos de cada país e os seis documentos UNESCO para comparação internacional. UNESCO e PISA/OCDE são grupos de referência, não países.

A agregação por país não significa que todos os países tenham o mesmo número de documentos. Essa diferença deve ser registrada como limitação e considerada na interpretação dos resultados.

## 3. Tradução e controle de repetição

Quando necessário, a tradução é realizada pela API da OpenAI. O builder mantém o texto original separado do texto em inglês e guarda traduções bem-sucedidas em `translation_cache.json`, usando o hash do texto como chave. Assim, uma nova execução reutiliza traduções já realizadas e não repete chamadas pagas para documentos inalterados.

A tradução deve ser executada antes da análise:

```bash
python rag_project/build_dataset.py \
  --corpus corpus \
  --out corpus/dataset_output \
  --translate
```

A chave da API deve ser carregada apenas pelo `.env` local ou por variável de ambiente. Nunca deve ser registrada no Git.

Na implementação atual, cada chamada traduz uma amostra de até 7.000 caracteres
por documento, para controlar custo e tamanho da requisição. Assim, o dataset inglês
é adequado para uma análise exploratória de vocabulário, mas não deve ser descrito
como tradução integral. Para a versão final da dissertação, é necessário decidir
entre traduzir o documento completo em blocos ou analisar o corpus original com
modelos multilíngues.

## 4. Cálculo do TF-IDF

O TF-IDF combina a frequência de um termo no documento com sua raridade na coleção. Para um termo $t$ em um documento $d$, a formulação pode ser expressa como:

$$
TFIDF(t,d) = TF(t,d) \times IDF(t)
$$

em que:

$$
IDF(t) = \log\left(\frac{N + 1}{DF(t) + 1}\right) + 1
$$

$N$ representa o número de documentos e $DF(t)$ o número de documentos que contêm o termo. Termos frequentes em um documento, mas pouco frequentes na coleção, recebem maior peso distintivo.

O script utiliza unigramas e bigramas, remove stopwords multilíngues frequentes, ignora tokens muito curtos e limita o vocabulário a 10.000 termos. Expressões como `digital citizenship` e `computational thinking` podem, assim, ser analisadas como unidades de sentido.

## 5. Similaridade entre países

A similaridade entre grupos é calculada pelo cosseno entre os vetores TF-IDF agregados. Para dois vetores $A$ e $B$:

$$
cos(A,B) = \frac{A \cdot B}{||A||\,||B||}
$$

Valores próximos de 1 indicam maior proximidade lexical na representação utilizada. Valores próximos de 0 indicam vocabulários mais distintos. A medida não prova equivalência curricular nem relação causal; ela indica proximidade textual sob os parâmetros definidos.

A UNESCO é mantida como grupo de referência separado e pode ser comparada individualmente com cada país. Ela não entra na matriz de similaridade entre países. O ranking de proximidade com UNESCO deve ser interpretado junto com os trechos recuperados pelo RAG e com a análise documental.

## 6. Arquivos de saída

O comando principal é:

```bash
python rag_project/analyze_tfidf.py \
  --input corpus/dataset_output/dataset_english.jsonl \
  --out corpus/analysis_output
```

São produzidos:

- `document_tfidf.csv`: pesos dos termos por documento;
- `document_top_terms.csv`: termos mais relevantes por documento;
- `group_tfidf.csv`: termos mais relevantes por país e UNESCO;
- `group_frequency.csv`: frequência absoluta dos termos por grupo;
- `group_similarity.csv`: pares de grupos e similaridade;
- `group_similarity_matrix.csv`: matriz completa de similaridade;
- `country_similarity_ranking.csv`: proximidade de cada país com UNESCO e Brasil;
- `group_similarity_heatmap.png`: representação visual da matriz;
- `top_terms_groups.png`: gráfico dos termos relevantes;
- `analysis_summary.json`: parâmetros, quantidade de documentos, grupos e vocabulário.

Os arquivos gerados são resultados derivados e permanecem fora do Git por meio do `.gitignore`. A análise pode ser reproduzida a partir do corpus, do dataset e dos parâmetros do comando.

## 7. Leitura dos resultados

A interpretação deve seguir quatro movimentos:

1. identificar termos de alto peso em cada documento e grupo;
2. observar termos compartilhados entre países;
3. comparar a proximidade lexical de cada país com UNESCO;
4. retornar aos documentos originais e ao RAG para conferir o contexto dos termos.

Um termo com alto TF-IDF não é automaticamente mais importante do ponto de vista pedagógico. Ele pode ser distintivo por aparecer em uma única política, por refletir uma tradução específica ou por estar relacionado ao vocabulário institucional de um país.

## 8. Relação com a Educação Comparada

O TF-IDF oferece evidência quantitativa para a comparação, mas não elimina a contextualização histórica, institucional e cultural. Convergências lexicais podem indicar uma agenda internacional compartilhada, enquanto divergências podem revelar diferentes concepções de computação, cidadania digital, ética, inclusão e formação docente.

As conclusões devem distinguir:

- recorrência lexical;
- proximidade textual;
- alinhamento temático;
- interpretação curricular.

Somente a última dimensão permite afirmar algo sobre sentidos formativos, e ela depende da leitura crítica dos documentos.

## 9. Comparação pelo DLGF 2018

O DLGF 2018 é a única matriz internacional usada para organizar evidências de competências digitais. O TF-IDF permanece exploratório: frequências e similaridades lexicais não provam correspondência curricular nem qualidade. A comparação final considera somente currículos e diretrizes oficiais nacionais incluídos e validados, com evidências conferidas por país, documento e página.

## 10. Limitações atuais

A primeira execução foi realizada com o arquivo inglês estruturalmente completo e
com amostras traduzidas via API. Por isso, ela é exploratória. A versão final deve
ser calculada após tradução integral em blocos, ou explicitamente apresentada como
análise baseada em amostras traduzidas. Em ambos os casos, deve registrar:

- data da geração;
- modelo utilizado na tradução;
- quantidade de documentos traduzidos;
- quantidade de falhas ou fallback para o original;
- parâmetros do vetor TF-IDF;
- quantidade de documentos por país;
- tratamento dos documentos UNESCO.

A tradução automática também exige conferência amostral, sobretudo para termos técnicos, nomes institucionais e conceitos curriculares.

## 11. Reprodutibilidade

A etapa é reproduzida em duas fases:

```bash
python rag_project/build_dataset.py --corpus corpus --out corpus/dataset_output --translate
python rag_project/analyze_tfidf.py --input corpus/dataset_output/dataset_english.jsonl --out corpus/analysis_output
```

As respostas do RAG podem então ser usadas para recuperar evidências dos padrões identificados. O TF-IDF, a similaridade e o RAG devem ser apresentados como métodos complementares dentro da triangulação da pesquisa.

## 12. Princípios orientadores da análise

Esta etapa segue os princípios de Computação Aplicada às Humanidades Digitais:

- a pergunta orienta a escolha do método;
- a unidade de análise é declarada antes do cálculo;
- corpus, metadados, indicadores PISA e textos são diferenciados;
- exploração descritiva não é confundida com explicação causal;
- frequência e similaridade são evidências auxiliares, não interpretações prontas;
- os resultados são conferidos nos documentos originais;
- erros, ausências, vieses de seleção e diferenças linguísticas são registrados;
- código e parâmetros permitem reproduzir a análise;
- a API da OpenAI e o RAG apoiam o tratamento, mas a interpretação permanece humana.

Um ranking textual não deve ser apresentado como julgamento de qualidade curricular. Alta similaridade com a UNESCO não prova implementação efetiva; vocabulário diferente também não prova ausência de alinhamento.

## 13. Procedimento reproduzível para todos os países

Para comparar perfis lexicais de países com idiomas diferentes, a análise deve usar traduções para um idioma comum. O procedimento abaixo reutiliza a tradução em cache, valida a cobertura de todas as páginas antes do cálculo e ajusta o TF-IDF separadamente dentro de cada país. Os escores não são comparados numericamente entre países.

Na raiz do projeto, com o ambiente virtual ativo e `OPENAI_API_KEY` disponível em `rag_project/.env` ou no ambiente, execute:

```bash
./.venv/Scripts/python -m rag_project.run_tfidf_all_countries \
  --run-id todos_paises_exploratorio_20260927_01
```

No Linux/macOS, substitua o executável por `python`. O comando usa `dataset_original_pages.jsonl` como fonte, traduz as páginas com `gpt-4o-mini`, reutiliza `translation_cache.json` e não cria Vector Store nem índice FAISS. Se uma execução for interrompida, rode novamente com o mesmo `--run-id`: o arquivo inglês parcial é reconstruído desde a origem e as traduções concluídas são recuperadas da cache.

Antes de calcular o TF-IDF, o comando exige que cada `content_id` da origem esteja representado por um ou mais segmentos ingleses, sem páginas ausentes, países divergentes ou segmentos sem status de tradução. Se a cobertura falhar, a execução para e registra estado parcial em `tfidf_run_manifest.json`; nenhum resultado é apresentado como completo.

Cada execução cria uma nova pasta em `dados_intermediarios/analise_lexical/tfidf_all_countries_<timestamp>/`, contendo o dataset traduzido, relatório de tradução, manifesto da execução e subpasta `analysis/` com:

- `country_profiles.csv`: um perfil/status por país e os principais termos;
- `country_local_top_terms.csv`: pesos TF-IDF e documentos em que cada termo ocorre;
- `country_local_frequency.csv`: frequências lexicais brutas, sem interpretação como competência;
- `analysis_summary.json`: países, documentos, estados e limites do cálculo;
- `top3_terms_by_country.png`: prancha com os três termos de cada país, em escalas independentes;
- `countries/<país>_tfidf_top3.png`: um gráfico por país, inclusive painel informativo quando não há contraste IDF;
- `tfidf_run_manifest.json`: hashes dos datasets/cache, cobertura por país, modelo, parâmetros, filtros, gráficos e caminhos dos artefatos.

Uma cópia versionável da prancha e dos gráficos individuais é exportada para `assets/<nome-da-execução>/`. Os CSVs, datasets traduzidos e manifestos operacionais permanecem em `dados_intermediarios/` e `dados_derivados/`, que são saídas locais ignoradas pelo Git.

O cálculo inclui os países presentes no dataset original e exige um perfil para cada um. Quando há apenas um documento, o vetor TF-IDF também é calculado e seus termos são exibidos, mas o perfil recebe `single_document_no_idf_contrast`: nesse caso, o IDF é 1 para todos os termos e o ranking é essencialmente uma frequência TF normalizada, sem contraste entre documentos. Traduções com japonês, chinês ou coreano passam pelo mesmo fluxo, pois o tokenizador recebe o texto traduzido para inglês; o texto original continua disponível no dataset-fonte e no campo `original_text` dos segmentos traduzidos.

### Limpeza e filtros efetivamente aplicados

Esta etapa **não remove cabeçalhos, rodapés, números de página ou elementos recorrentes do layout**. Se esses elementos estiverem no texto extraído, podem afetar frequência e pesos TF-IDF. O manifesto registra `header_footer_cleaning=false`; qualquer limpeza posterior deve ser feita em um campo derivado de análise, mantendo intacto o texto original para rastreabilidade.

O tokenizador usa unigramas e bigramas, aceita sequências de pelo menos três caracteres (`token_pattern=\\b\\w{3,}\\b`), limita o vocabulário a 10.000 termos e remove as stopwords listadas em `rag_project/analyze_tfidf.py`. Neste procedimento intrapaís, `min_df=1` e `max_df=1.0`, portanto não há exclusão adicional por raridade ou por alta frequência documental. As stopwords são filtradas do cálculo, não apagadas dos textos de origem ou tradução.

### Estado em 03/10/2026

A execução multilíngue anterior usou 9.042 páginas originais de 22 países sem tradução comum; ela é exploratória e não deve ser tomada como TF-IDF comparável entre países. Em 03/10/2026, `run_tfidf_all_countries` traduziu as 9.042 páginas em 19.497 segmentos ingleses, verificou cobertura integral e gerou perfis para os 22 países. O Japão está incluído com 907 páginas. O resumo registrou 21 países em `within_country_only` e um país com um único documento (`single_document_no_idf_contrast`). A primeira tentativa parcial, com 507 segmentos só da África do Sul, foi substituída pela reconstrução completa a partir da origem e da cache.

Na conferência dos termos japoneses, palavras funcionais inglesas ainda apareciam entre as mais relevantes. A lista de stopwords foi ampliada com `sklearn.feature_extraction.text.ENGLISH_STOP_WORDS` e os resultados finais foram regenerados em `tfidf_all_countries_20261003T161344Z`. No Japão, palavras como `that`, `will` e `should` deixaram de aparecer no top 20; termos como `students`, `learning`, `education`, `technology` e `data` permaneceram. Os Estados Unidos também aparecem com termos e status `single_document_no_idf_contrast`. A prancha geral e os 22 PNGs individuais foram exportados para `assets/tfidf_all_countries_20261003T161344Z/`. O manifesto registra a lista efetiva de stopwords e os hashes dos arquivos usados.

### Execução exploratória em 27/09/2026

O TF-IDF da rodada `todos_paises_exploratorio_20260927_01` foi calculado com
`source_text` do dataset original em páginas, sem tradução para um idioma comum:

```bash
python -m rag_project.analyze_tfidf \
  --input dados_intermediarios/pipeline_runs/todos_paises_exploratorio_20260927_01/datasets/dataset_original_pages.jsonl \
  --text-field source_text \
  --out dados_intermediarios/analise_lexical/todos_paises_exploratorio_20260927_01
```

A entrada continha 9.042 páginas de 93 documentos com texto nos 22 países; no
manifesto da execução, 36 páginas estavam associadas a fontes `validated` e 9.006
a fontes `pending_review`. Em 03/10/2026, a pesquisadora confirmou a validação
humana dos 94 arquivos e o registro vigente foi reconciliado; os rótulos do
manifesto permanecem como fotografia histórica daquela execução. As sete áreas
do DLGF foram adicionadas separadamente como referência lexical, totalizando
100 unidades documentais no cálculo. O JSONL não registra o idioma por página e
preserva os idiomas originais. Portanto, os resultados são exploratórios: não
devem ser interpretados como comparação lexical normalizada, ranking de países
ou evidência de alinhamento curricular. Para comparação entre idiomas, use uma
tradução consistente e registre o modelo, a cobertura e as falhas da tradução.

## 14. TF-IDF somente em relação ao UNESCO DLGF 2018

Para comparar os perfis nacionais somente com o referencial UNESCO, use o modo `--dlgf-only` sobre o dataset inglês completo:

```bash
./.venv/Scripts/python -m rag_project.analyze_tfidf \
  --dlgf-only \
  --input dados_intermediarios/pipeline_runs/todos_paises_exploratorio_20260927_01/datasets/dataset_english_pages_tfidf.jsonl \
  --text-field english_text
```

O modo agrega documentos por país e compara o vetor médio de cada perfil com as sete áreas do `DLGF_2018`. Não calcula similaridade entre países nem inclui PISA ou outros frameworks. O vocabulário do TF-IDF é ajustado conjuntamente sobre os documentos nacionais em inglês e as sete representações das áreas. O CSV do DLGF do projeto contém termos em inglês e português; essa representação lexical bilíngue deve ser considerada na leitura dos valores.

Cada execução gera uma pasta `tfidf_dlgf_only_<timestamp>/` com `country_dlgf_area_similarity.csv` (uma linha por país e área), `country_dlgf_area_similarity_matrix.csv`, `country_dlgf_area_similarity_heatmap.png` e `analysis_summary.json`. A figura é copiada para `assets/tfidf_dlgf_only_<timestamp>/`. O resumo registra hashes de entrada e framework, parâmetros, países incluídos e que nenhuma comparação país-país foi calculada.

Os valores são similaridades lexicais exploratórias, não prova de adoção do DLGF, cobertura de competência ou alinhamento curricular. Não devem ser usados isoladamente como classificação ou ranking de países; cada correspondência exige leitura contextual e validação humana.
