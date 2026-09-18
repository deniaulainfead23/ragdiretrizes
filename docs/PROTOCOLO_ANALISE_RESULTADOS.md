# Protocolo de análise dos resultados

## Finalidade

Este documento orienta a passagem da rodada técnica do RAG para a análise científica da pesquisa **Diretrizes Curriculares de Computação e Educação Digital na Educação Básica: uma análise comparativa internacional orientada à formação do cidadão do futuro**.

A finalidade não é produzir um ranking de países nem substituir a leitura dos documentos por uma resposta automática. O RAG será utilizado como instrumento de localização e organização de evidências. A interpretação comparativa continuará sob responsabilidade da pesquisadora.

## Estado da rodada oficial

A rodada oficial registrada em `analysis/official_run_20260912` foi organizada em duas camadas:

1. **Q01 a Q13**: recuperação de evidências por país.
2. **Q14**: comparação internacional construída somente a partir das respostas nacionais e das evidências já recuperadas.

O fechamento técnico registra:

| Elemento | Estado |
|---|---|
| Respostas Q01 a Q13 | 286 |
| Respostas inconclusivas | 3 |
| Base de entrada da Q14 | 286 linhas |
| Comparações temáticas da Q14 | 13 |
| Q14 final | Gerada e sujeita à validação semântica |
| PISA 2022 | Variável contextual de seleção, não validador curricular |
| OECD Digital Education Outlook 2023 | Referencial complementar de discussão, externo ao corpus principal |

Uma resposta `inconclusive` significa insuficiência de evidência recuperada para responder à pergunta. Não significa ausência do conceito no currículo, no documento ou no país.

## Fio lógico da análise

A análise deverá seguir a cadeia de proveniência:

`run_id -> question_run_id -> question_id -> response_id -> evidence_id -> document_id -> página ou trecho`

Cada afirmação incluída na dissertação deverá ser classificada como:

- **evidência documental**: trecho identificável no documento original;
- **síntese computacional**: organização de evidências produzida pelo pipeline;
- **interpretação da pesquisadora**: leitura comparativa contextualizada;
- **referencial de discussão**: contribuição da UNESCO, OCDE, BNCC ou outra fonte complementar.

A síntese computacional nunca deverá ser apresentada como se fosse uma citação direta do documento.

## Relação entre objetivos e resultados

| Objetivo específico | Perguntas principais | Produto analítico |
|---|---|---|
| Identificar competências, habilidades e valores | Q01, Q03, Q05 | Matriz de competências, valores e evidências por país |
| Mapear Computação, cultura digital e pensamento computacional | Q01, Q02, Q06 | Perfil curricular por país e síntese temática |
| Comparar convergências e divergências | Q01 a Q13, com Q14 | Matriz comparativa validada, sem ranking automático |
| Analisar aproximações com a UNESCO | Q04, Q11 e categorias do framework | Matriz de evidências classificadas como explícitas, implícitas ou não identificadas |

## Ordem recomendada de análise

### 1. Conferência da base

Verificar a presença e a integridade de:

- `document_id`;
- país e grupo do corpus;
- título do documento;
- página inicial e final;
- `chunk_id`;
- texto original ou texto processado;
- pergunta e versão da pergunta;
- classificação e status da evidência;
- observações de validação humana.

### 2. Validação por país

Para cada país, revisar Q01 a Q13 na seguinte ordem:

1. ler a resposta consolidada;
2. abrir as evidências associadas;
3. conferir o documento e a página;
4. comparar o trecho original com a tradução, quando houver;
5. classificar a evidência como explícita, implícita, insuficiente ou inadequada;
6. registrar a decisão e a justificativa;
7. separar ausência de evidência de evidência de ausência.

### 3. Síntese temática

Depois da validação por país, organizar os achados nos seguintes eixos:

- definição e organização das competências digitais;
- pensamento computacional e algoritmos;
- cidadania digital, ética e letramento midiático;
- relação com UNESCO e cidadania global;
- competências associadas ao século XXI;
- criatividade, colaboração e resolução de problemas;
- inteligência artificial, dados e segurança;
- inclusão digital e equidade;
- ênfase técnica e ênfase sociocultural;
- pensamento crítico, letramento midiático e participação democrática.

### 4. Comparação internacional

A Q14 deverá ser usada como ponto de partida para a comparação, não como texto final pronto. Cada resultado comparativo deverá ser conferido contra as matrizes nacionais.

A redação deverá privilegiar formulações como:

- os documentos analisados apresentam;
- foram identificadas evidências de;
- observa-se uma tendência de;
- a presença aparece de forma explícita ou implícita;
- a comparação sugere aproximações e diferenças;
- não foi localizada evidência suficiente para afirmar.

Devem ser evitadas formulações absolutas como:

- o país é o melhor;
- o país possui o currículo mais avançado;
- o país não trabalha determinado tema;
- a similaridade textual comprova alinhamento curricular.

## Uso correto das técnicas

### RAG

O RAG recupera trechos relevantes para as perguntas analíticas. Sua função principal é apoiar a localização, a comparação e a rastreabilidade das evidências.

### TF-IDF

O TF-IDF descreve a distribuição lexical e destaca termos distintivos em documentos ou grupos. Ele não mede qualidade curricular, importância pedagógica, inovação, desenvolvimento nacional ou alinhamento substantivo.

### Similaridade cosseno

A similaridade cosseno indica proximidade lexical entre representações textuais. Ela não comprova equivalência curricular, semelhança cultural ou convergência de políticas educacionais.

### Tradução e OCR

A tradução e o OCR são mediações metodológicas. O texto original deve ser preservado, a tradução deve ser identificada e os trechos decisivos devem ser conferidos manualmente. Documentos com OCR problemático devem permanecer marcados para revisão.

## Critérios para transformar uma evidência em resultado

Uma evidência só deverá sustentar uma afirmação na dissertação quando:

1. estiver vinculada a um documento identificável;
2. possuir localização por página, seção ou trecho;
3. responder à pergunta analítica correspondente;
4. não depender apenas de uma palavra isolada;
5. estiver compatível com o contexto curricular;
6. tiver sido submetida à validação humana;
7. permitir que outra pessoa reproduza a conferência.

## Estrutura de cada subseção de resultados

Cada subseção do capítulo de resultados deverá seguir quatro movimentos:

1. **O que foi perguntado**: apresentar o eixo analítico e a relação com o objetivo.
2. **O que foi encontrado**: sintetizar os padrões com base nas evidências.
3. **Como os países diferem**: apresentar variações de organização, ênfase e contexto.
4. **O que isso significa para a pesquisa**: interpretar o achado em relação ao cidadão do futuro, ao Brasil e aos referenciais adotados.

Esse formato evita a repetição de respostas e mantém a ligação entre metodologia, resultado e discussão.

## Regras de escrita

- preservar a voz da pesquisadora e o caráter crítico da Educação Comparada;
- evitar parágrafos que apenas repitam a pergunta;
- não transformar termos frequentes em competências comprovadas;
- distinguir documento curricular de referencial complementar;
- indicar quando a evidência é parcial ou inconclusiva;
- não usar travessões no texto corrido;
- evitar repetir a mesma conclusão em subseções diferentes;
- apresentar a limitação junto da interpretação quando ela afetar o resultado;
- manter a diferença entre descrição, comparação e interpretação.

## Próximo ciclo de trabalho

1. Validar os arquivos exportados de Q01 a Q13.
2. Fechar a matriz de evidências por país.
3. Revisar a Q14 temática por temática.
4. Selecionar evidências representativas para cada eixo.
5. Reescrever o capítulo de resultados com a estrutura de quatro movimentos.
6. Confrontar a síntese com os objetivos específicos.
7. Atualizar conclusões, contribuições e limitações somente depois do fechamento da matriz.
8. Gerar o manifesto final da rodada, incluindo versões, hashes, perguntas, frameworks e decisões de validação.

## Princípio central

A tecnologia amplia a capacidade de leitura da pesquisa, mas a conclusão científica nasce da relação entre documento, contexto, evidência, comparação e interpretação crítica.
