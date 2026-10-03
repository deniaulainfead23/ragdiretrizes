# Estado Atual dos Resultados

Atualizado em 03/10/2026.

## Fonte de conteúdo vigente

O único documento de referência para a análise consolidada é `dados_derivados/analysis/todos_paises_exploratorio_20260927_01/human_validation/analise_consolidada_22_paises_DLGF_2018.docx`, elaborado com conferência humana. Dentro de `human_validation`, os outros arquivos são artefatos de processamento/validação e não substituem nem alteram as instruções desse DOCX.

A pesquisadora confirmou que todos os 94 arquivos da lista curada foram examinados e validados humanamente. O registro vigente do corpus foi reconciliado com essa confirmação. Os status 4 `validated`/90 `pending_review` preservados em manifests de rodadas anteriores descrevem o estado capturado à época; a validação dos arquivos não significa que cada página, citação RAG ou correspondência DLGF tenha sido conferida individualmente.

## Artefatos vigentes

- `dados_derivados/analysis/todos_paises_exploratorio_20260927_01/human_validation/matriz_dlgf_22_paises_relatorio_consolidado.xlsx`: matriz de síntese dos 22 países e sete áreas DLGF, derivada do DOCX. Estados: `supporting`, `contextual`, `not_assessed` e `no_evidence_after_defined_review`.
- `dados_derivados/analysis/todos_paises_exploratorio_20260927_01/human_validation/mapa_paginas_corpus_avaliacao_1.xlsx`: mapa preliminar de paginação dos 94 PDFs nacionais e 9.279 páginas físicas. É a Avaliação 1 automatizada, não validação visual final. Os registros com `review_required=yes` ficam para a Avaliação 2 após a qualificação.
- `docs/resultados_preliminares_rag_avaliacao_1.md`: síntese preliminar das 286 respostas RAG de Q01–Q13 para os 22 países; 266 estão `candidate` e 20 `inconclusive`, com 619 registros de evidência. Q04 foi refeita por buscas direcionadas, mas suas áreas continuam candidatas até revisão.

## Uso de resultados anteriores

Os resultados RAG da Avaliação 1 podem ser apresentados ao lado da síntese humana, desde que identificados como preliminares e sem promover `candidate` a validado. Rodadas RAG antigas, dataset bilíngue com tradução defeituosa, classificações lexicais e matrizes corrigidas por versões incompatíveis permanecem históricas; não combiná-las com a rodada atual. Falha de recuperação, extração ou tradução não deve ser convertida em zero ou ausência curricular.

## Próxima etapa

Usar a síntese humana e os resultados RAG da Avaliação 1 na preparação para a qualificação, sempre distinguindo interpretação humana de saída candidata do modelo. Depois, realizar a Avaliação 2 das páginas/citações prioritárias e das pendências de OCR/tradução apontadas no relatório.
