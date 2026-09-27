# Organização dos dados e dos resultados

## Finalidade

Este documento estabelece a organização física e analítica do projeto sem alterar o título da dissertação:

**Currículos e diretrizes oficiais de Computação e Educação Digital na Educação Básica: análise comparativa entre países e pelo DLGF 2018.**

A expressão do título é mantida como horizonte formativo da pesquisa. A análise empírica permanece concentrada no que os documentos curriculares e normativos explicitam sobre Computação, Educação Digital e competências relacionadas.

## Três camadas de dados

| Camada | O que contém | Pode ser alterada? | Uso na pesquisa |
|---|---|---:|---|
| Dados brutos | Fontes oficiais, PDFs originais, arquivos de origem e manifestos | Não | Preservação e rastreabilidade |
| Dados intermediários | OCR, extração, tradução, normalização, segmentação, metadados, datasets e análises exploratórias | Sim, com versão | Preparação e processamento |
| Dados derivados | Respostas, evidências, matrizes, comparações, tabelas, gráficos e relatórios | Sim, com registro | Análise e apresentação dos resultados |

## Matriz analítica externa

O DLGF 2018 é a única matriz externa usada para organizar evidências de competências digitais. Ele não integra a contagem de países nem substitui a comparação entre currículos nacionais.

As categorias de leitura dos documentos incluem:

- competências digitais e letramento digital;
- pensamento computacional;
- cidadania digital, ética e letramento midiático;
- segurança, inclusão e equidade;
- organização curricular e formação docente.

As áreas do DLGF são aplicadas apenas quando a evidência nacional sustentar a correspondência.

## Organização dos resultados

O capítulo de resultados deve ser montado em cinco movimentos:

### 1. Fechamento técnico do corpus

Apresentar quantidade de países, documentos, idiomas, documentos processados, registros de conteúdo e situação da auditoria.

### 2. Resultados por pergunta

Para cada pergunta Q01 a Q13, apresentar:

- objetivo analítico da pergunta;
- evidências validadas;
- padrões encontrados;
- diferenças entre os países;
- casos inconclusivos ou limitações;
- interpretação relacionada ao objetivo específico.

### 3. Matriz de competências

Organizar as evidências segundo as áreas do UNESCO/UIS 2018, preservando também as categorias próprias de pensamento computacional e cidadania.

A codificação deve distinguir:

- evidência explícita;
- evidência implícita ou contextual;
- evidência insuficiente;
- não identificada no material recuperado;
- pendente de validação.

### 4. Comparação internacional

A comparação Q14 deve ser construída somente depois da revisão das respostas nacionais. Ela deve sintetizar convergências, diferenças de organização curricular, ênfases técnicas e socioculturais e lacunas documentais.

Não deve produzir ranking de países nem afirmar que um país é melhor ou mais avançado sem desenho metodológico específico para isso.

### 5. Síntese interpretativa

A interpretação deve relacionar os resultados ao problema, aos objetivos e ao título da pesquisa. O texto deve afirmar o que os documentos prescrevem ou explicitam, sem afirmar que a pesquisa mediu implementação, aprendizagem, efetividade ou formação real dos estudantes.

## Cadeia de rastreabilidade

Toda afirmação usada na dissertação deve poder ser conferida pela cadeia:

```text
run_id
→ question_run_id
→ question_id
→ response_id
→ evidence_id
→ document_id
→ página ou trecho
```

## Compatibilidade com os arquivos atuais

A rodada oficial existente possui artefatos históricos em diretórios legados, como `analysis/`, `countries/`, `data/` e `metadata/`. Eles não devem ser apagados ou movidos automaticamente, porque scripts e manifestos ainda utilizam esses caminhos.

A organização em `dados_brutos/`, `dados_intermediarios/` e `dados_derivados/` será adotada como estrutura de referência para novos arquivos e para a migração controlada. A migração somente deve ocorrer depois de atualizar os scripts, testar a rodada completa e conferir os hashes dos arquivos.

## Regra central

O RAG localiza e organiza evidências. A pesquisadora valida, compara e interpreta. A conclusão científica resulta da relação entre documento, contexto, evidência, comparação e interpretação crítica.
