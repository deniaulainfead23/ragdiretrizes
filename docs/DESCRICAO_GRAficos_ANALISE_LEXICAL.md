# Descrição dos gráficos da análise lexical exploratória

## Contexto metodológico

Esta documentação descreve os gráficos gerados no fluxo de análise lexical exploratória do projeto RAG Diretrizes. Ela foi elaborada para manter coerência com a metodologia da pesquisa e com a regra de interpretação adotada: os resultados de TF-IDF e similaridade textual são auxiliares, exploratórios e não equivalem a avaliação curricular, alinhamento documental nem prova causal.

A análise lexical deve ser lida como uma etapa de mapeamento do vocabulário e da organização textual dos documentos. Sua função é identificar padrões de recorrência, proximidade lexical e diferenciação terminológica entre países e entre os documentos comparados. A interpretação substantiva continua sendo feita pela leitura documental, pela triangulação com o referencial teórico e pelo uso do sistema RAG com rastreabilidade.

Os gráficos aqui descritos são produzidos a partir dos indicadores gerados em `corpus/analysis_output` e devem ser interpretados em conjunto com os CSVs correspondentes, com os documentos originais e com a descrição metodológica do projeto.

---

## 1. `lexical_group_similarity_heatmap.png`

### Finalidade

Apresenta a matriz de similaridade lexical entre os grupos nacionais considerados na análise.

### O que representa

Cada célula da matriz indica o grau de proximidade textual entre dois grupos, calculado por similaridade cosseno a partir do TF-IDF agregado por país. Valores mais próximos de 1 sugerem vocabulários mais semelhantes sob a representação textual utilizada. Valores mais próximos de 0 indicam vocabulários mais distintos.

### Como interpretar

- A matriz é útil para identificar clusters de países com vocabulários próximos.
- Ela não deve ser interpretada como indício de equivalência curricular.
- A similaridade aqui é lexical e computacional, e não prova que dois currículos possuem a mesma abordagem pedagógica ou a mesma concepção de educação digital.
- A leitura mais segura é: “há proximidade de vocabulário” e não “há alinhamento curricular”.

### Uso na pesquisa

Essa visualização apoia a etapa exploratória da análise comparativa, favorecendo a identificação de padrões gerais de linguagem e de proximidade estrutural entre as políticas curriculares.

---

## 2. `lexical_top_terms_groups.png`

### Finalidade

Apresenta os termos mais relevantes por grupo no conjunto de documentos analisados.

### O que representa

Os termos destacados refletem os pesos de TF-IDF mais altos para cada país ou grupo. Em outras palavras, eles são termos que se sobressaem no vocabulário do grupo comparado, considerando sua frequência no documento e sua raridade no conjunto.

### Como interpretar

- Termos de maior peso sugerem cenários textuais mais específicos ou mais distintivos.
- Eles podem sinalizar temas recorrentes e estruturas institucionais do documento.
- Alguns termos podem aparecer por convenções editoriais, nomes de ministérios, referências geográficas, documentos legais ou vocabulário institucional, e não necessariamente por uma intenção curricular explícita.

### Atenção metodológica

O gráfico deve ser lido como mapa do vocabulário, não como ranking de qualidade ou valor curricular. O simples fato de um país usar certos termos com maior peso não significa que tenha melhor ou pior desenho pedagógico.

---

## 3. `brazil_country_similarity.png`

### Finalidade

Visualiza a proximidade textual de cada país em relação ao Brasil.

### O que representa

Cada barra indica a similaridade cosseno entre o perfil TF-IDF do Brasil e de outro país. O gráfico permite observar quais países apresentam maior semelhança lexical com o Brasil sob o modelo computacional estabelecido.

### Como interpretar

- A ordenação mostra padrões de vocabulário compartilhado entre Brasil e os outros casos.
- Países mais próximos do Brasil podem apresentar maior coincidência de termos e estruturas textuais.
- Isso não indica equivalência curricular, similaridade de política pública nem alinhamento pedagógico.

### Uso na pesquisa

Esse gráfico é útil para contextualizar o Brasil em relação ao conjunto comparado. Ele pode orientar a leitura documental, mas sempre deve ser triangulado com análise crítica dos documentos, temas e categorias curriculares.

---

## 4. `country_unesco_similarity.png`

### Finalidade

Apresenta a proximidade textual dos países em relação à UNESCO, como referência documental internacional.

### O que representa

Cada barra mostra a similaridade entre o perfil lexical de um país e o perfil lexical da UNESCO, construído a partir do corpus comparado. Esse gráfico faz uma referência explícita entre o grupo documental UNESCO e os países analisados.

### Como interpretar

- Ele fornece um mapeamento de proximidade lexical com a linha de base documental UNESCO.
- A comparação é válida como referência metodológica, desde que mantida separada da avaliação do currículo nacional.
- A semelhança lexical com UNESCO não equivale a adesão de um país ao mesmo marco conceitual, nem a garantia de implementação curricular.

### Limite metodológico

A UNESCO deve ser entendida como referência de análise e base documental comparativa, e não como um país do conjunto comparado. Por isso, a referência à UNESCO deve ser interpretada como comparação contextual e de referencial, e não como ranking entre pares curriculares.

---

## 5. `brazil_unesco_terms_heatmap.png`

### Finalidade

Mostra os termos mais relevantes para Brasil e UNESCO em uma matriz comparativa.

### O que representa

A matriz organiza termos em linhas e grupos em colunas, permitindo observar quais palavras têm maior peso no vocabulário de cada referência comparada. A intensidade da cor indica o peso TF-IDF do termo no grupo.

### Como interpretar

- O gráfico ajuda a localizar termos compartilhados ou distintos entre Brasil e UNESCO.
- Pode sinalizar convergências de vocabulário em temas como cidadania, tecnologia, ética, participação e aprendizagem.
- Também pode revelar diferenças de formulação institucional, especialmente em expressões próprias da linguagem curricular nacional.

### Atenção

Aqui também vale a regra metodológica: o simples peso lexical não define importância substantiva. O gráfico não deve ser usado como prova de alinhamento ou de superioridade curricular.

---

## 6. `lexical_group_similarity.csv`

### Finalidade

Arquivo tabular que registra as similaridades entre os grupos nacionais.

### O que representa

Cada linha contém um par de grupos e a similaridade calculada entre eles.

### Como interpretar

- É a base estruturada para a matriz de calor e para a leitura comparativa entre países.
- Permite uma análise mais detalhada e reprodutível dos valores numéricos.
- Serve como material de apoio para relatórios e triangulação metodológica.

### Uso metodológico

Esse CSV deve ser lido como evidência quantitativa exploratória, e não como resultado definitivo de equivalência curricular.

---

## 7. `lexical_group_tfidf.csv`

### Finalidade

Lista os termos de maior peso TF-IDF por grupo país.

### O que representa

Cada linha indica o grupo, a posição do termo no ranking, o termo e seu valor TF-IDF.

### Como interpretar

- Os termos mais altos refletem o vocabulário mais distintivo de cada país no corpus.
- Podem revelar temas com maior centralidade na linguagem oficial do documento.
- Também podem captar ruído institucional, nomes de documentos, referências legais e padrões editoriais.

### Limite

Esse indicador não substitui a leitura documental. Um termo pode aparecer como relevante por razões formais e não necessariamente por ser central na lógica curricular.

---

## 8. `analysis_summary.json`

### Finalidade

Resumo dos parâmetros da execução.

### O que representa

Contém informação sobre o arquivo de entrada, a quantidade de documentos, os grupos incluídos, o tamanho do vocabulário, o modo de análise e a nota metodológica.

### Como interpretar

- O arquivo funciona como metadado operacional da análise.
- Registra se a execução foi de natureza exploratória e lexical.
- Permite rastreabilidade e reprodutibilidade da etapa computacional.

### Papel metodológico

É um artefato técnico de transparência, e não uma conclusão substantiva sobre currículo.

---

## Regra de leitura final

Os gráficos e CSVs da análise lexical devem ser usados da seguinte forma:

1. identificar padrões de vocabulário;
2. localizar proximidades textuais;
3. observar termos distintivos por país;
4. retornar aos documentos originais para interpretar o contexto;
5. evitar transformar similaridade textual em equivalência curricular.

Em síntese, a análise gráfica deste conjunto é um mapa de linguagem e proximidade lexical, e não uma prova de qualidade, alinhamento ou efetividade curricular.
