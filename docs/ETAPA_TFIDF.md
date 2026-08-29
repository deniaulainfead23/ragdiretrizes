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
2. grupo: agrega os documentos de cada país e os seis documentos UNESCO para comparação internacional.

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

A UNESCO é mantida como grupo separado e pode ser comparada individualmente com cada país. O ranking de proximidade com UNESCO deve ser interpretado junto com os trechos recuperados pelo RAG e com a análise documental.

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

## 9. Relação com UNESCO e PISA

A UNESCO funciona como linha de base normativa e formativa, especialmente para cidadania global, direitos humanos, inclusão, ética e responsabilidade social. O PISA/OCDE deve ser documentado como referencial internacional usado na seleção ou caracterização dos países e, quando seus dados forem cruzados com os resultados, deve ser tratado como contexto comparativo.

O TF-IDF não deve ser apresentado como explicação do desempenho no PISA. A pesquisa pode observar relações e contrastes entre vocabulário curricular e indicadores internacionais, mas não deve afirmar causalidade sem desenho específico para esse propósito.

O documento PISA 2022 presente em `corpus/pisa/` é tratado como grupo externo
`PISA/OECD`. Ele contextualiza a seleção dos países e não deve ser agregado a um
país nem usado como se fosse uma diretriz curricular. A comparação entre países
com maior desempenho no PISA e maior proximidade da UNESCO pode ser apresentada
como análise exploratória, desde que se declare que proximidade textual não prova
que o desempenho decorra do currículo.

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

### Estado atual da execução

O corpus atual contém 91 documentos, incluindo seis documentos UNESCO e um
documento PISA 2022. A tradução integral foi iniciada em blocos de 6.000
caracteres e 92 blocos foram preservados no cache. Como a execução foi interrompida
antes de concluir todos os documentos, o `dataset_english.jsonl` atual não deve ser
usado para resultados finais. A execução deve ser retomada com o mesmo comando;
os blocos já existentes no `translation_cache.json` serão reutilizados.
