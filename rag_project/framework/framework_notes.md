# Framework e stopwords da Fase 3

Este diretório registra os frameworks analíticos usados na comparação curricular e no pipeline de evidência.

## Frameworks ativos

- UNESCO_GCED_2015: dimensões cognitivas, socioemocionais e comportamentais da Educação para a Cidadania Global.
- UNESCO_DLGF_2018: referencial principal para competências/letramento digital, com as áreas 0 a 6 propostas no Information Paper No. 51 do UNESCO Institute for Statistics.
- COMPUTING_AND_DIGITAL_EDUCATION: competências de computação, alfabetização digital e ética digital.
- UNESCO_FUTURES_2021: eixo complementar de futuro, aprendizagem e resiliência.

## Regras de uso

- O framework deve ser declarado em cada pergunta do catálogo.
- A ausência de recuperação não deve ser interpretada como ausência conceitual.
- O pré-processamento deve preservar rastreabilidade da escolha de stopwords e regras.
- Os artefatos são versionados em 2.0 para manter compatibilidade com a etapa de perguntas.

## Delimitação entre GCED e DLGF

- O DLGF 2018 não substitui o GCED 2015. Os dois referenciais respondem a dimensões analíticas diferentes.
- O GCED 2015 permanece associado à cidadania global e às dimensões cognitiva, socioemocional e comportamental.
- O DLGF 2018 é usado para classificar evidências de competências/letramento digital.
- A classificação DLGF é uma camada analítica posterior sobre evidências já recuperadas; os resultados originais do RAG permanecem preservados.
- O mapeamento deve seguir abordagem de baixa inferência. Correspondências vagas ou ambíguas devem ser registradas como inconclusivas.
- Ausência de evidência recuperada não equivale a ausência conceitual no currículo.
- Contagens de evidências não representam qualidade curricular, desempenho, grau de implementação ou superioridade entre países.
