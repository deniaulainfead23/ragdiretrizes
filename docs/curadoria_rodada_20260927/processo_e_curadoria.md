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

O preflight encontrou divergências entre os arquivos locais, o registro documental e os status de aprovação. Por isso, nenhum dataset ou índice completo foi reconstruído e nenhuma nova resposta RAG foi gerada. A rodada deve permanecer bloqueada até a curadoria reconciliar documentos ausentes, não registrados e pendentes de validação.

O arquivo de referência que estava aberto durante a revisão não corresponde ao DLGF 2018; ele foi excluído da análise. A tabela operacional ativa do framework está em `rag_project/framework/unesco_dlgf_2018.csv`. A procedência do documento-fonte do DLGF deve ser confirmada antes de usar citações bibliográficas além das categorias registradas na tabela.
