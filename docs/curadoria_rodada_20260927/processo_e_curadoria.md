# Processo de curadoria e nova rodada

## Escopo vigente

A análise compara currículos e diretrizes oficiais dos países sobre Computação na Educação Básica. O DLGF 2018 é a única matriz internacional de competências digitais. O catálogo ativo contém Q01–Q14; Q01–Q13 recuperam evidências por país e Q14 compara evidências nacionais validadas. Não existe Q15 no catálogo.

A dimensão de cidadania global foi retirada do escopo. Cidadania digital, ética, letramento midiático, inclusão e participação permanecem apenas nas perguntas curriculares em que são pertinentes; não constituem framework externo separado.

## Regra de inclusão

Diretórios do corpus não aprovam documentos automaticamente. Cada item precisa estar no registro curado, corresponder a uma fonte oficial e à versão selecionada, ser pertinente à Educação Básica, ter páginas conferidas e receber status validado após revisão humana. O dataset deve conter apenas documentos nacionais validados e texto processado liberado.

O DLGF é mantido separado dos documentos curriculares. A associação de uma evidência às sete áreas exige trecho e página rastreáveis. Classificação lexical é preliminar e não substitui validação humana.

## Processamento da rodada

1. Inventariar documentos e confrontar arquivos com o registro curado.
2. Conferir autoria oficial, título, versão/ano, país, nível escolar, páginas e decisão de inclusão.
3. Extrair texto diretamente quando disponível; aplicar OCR somente onde necessário e revisar a saída.
4. Gerar dataset a partir de documentos nacionais aprovados e processados.
5. Construir embeddings e índice em diretório exclusivo da rodada.
6. Executar Q01–Q13 por país, revisar respostas nas fontes e validar evidências.
7. Gerar matriz DLGF e Q14 a partir das evidências aprovadas.

Cada rodada tem manifesto e saídas próprios. Credenciais ficam somente em configuração local ignorada pelo Git. Não sobrescrever corpus bruto nem resultados anteriores.

## Artefatos históricos e testes

Resultados de rodadas anteriores, incluindo respostas e comparações já produzidas, permanecem preservados como históricos. Não devem ser combinados com o catálogo atual nem apresentados como resultados da nova rodada. Testes automatizados em `tests/` continuam como código de verificação, não como corpus de pesquisa.

Os antigos artefatos de classificação que dependiam de dimensões fora do DLGF foram retirados do fluxo ativo. Os arquivos originais e relatórios de auditoria permanecem preservados quando necessários à proveniência; sua existência não significa inclusão na análise vigente.

## Situação em 27-09-2026

A rodada `todos_paises_exploratorio_20260927_01` reconciliou os 94 documentos registrados dos 22 países; os arquivos estavam presentes. O manifesto daquela execução capturou quatro documentos como `validated` e 90 como `pending_review`, produzindo 9.042 páginas (36 e 9.006, respectivamente). Esses rótulos são o estado operacional registrado na data da rodada. A pesquisadora informa que todos os 94 arquivos já haviam sido examinados e validados humanamente; em 03/10/2026, os 90 status remanescentes do registro vigente foram reconciliados para `validated`. A revisão humana dos arquivos não valida automaticamente cada página, citação RAG ou interpretação gerada; essas etapas mantêm seus próprios estados de revisão. As perguntas Q01–Q13 e seus resultados históricos não foram reescritos.

O TF-IDF da rodada foi calculado a partir de `dados_intermediarios/pipeline_runs/todos_paises_exploratorio_20260927_01/datasets/dataset_original_pages.jsonl`, usando `source_text`, com saída em `dados_intermediarios/analise_lexical/todos_paises_exploratorio_20260927_01/`. Os 93 documentos com texto foram agregados por `document_id`; as sete áreas do DLGF são unidades de referência adicionais. Como os textos estão nos idiomas originais e o dataset não registra o idioma por página, a análise lexical combinada é apenas exploratória e não sustenta ranking ou comparação quantitativa entre idiomas sem tradução consistente e validação.

O índice FAISS local não foi concluído por falta de memória; a recuperação desta rodada usou o Vector Store OpenAI. O DLGF permanece como referência, não como currículo nacional. A tabela operacional ativa está em `rag_project/framework/unesco_dlgf_2018.csv`; confirme a procedência bibliográfica do documento-fonte antes de usar citações além das categorias registradas na tabela.
