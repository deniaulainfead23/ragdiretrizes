# Projeto RAG para comparação curricular em Computação

## Objetivo

Analisar comparativamente como currículos e diretrizes oficiais da Educação Básica tratam a Computação e a Educação Digital em diferentes países. A comparação considera organização curricular, competências, conteúdos e dimensões sociais e éticas. O único referencial internacional usado como matriz de competências digitais é o Digital Literacy Global Framework (DLGF) de 2018.

A pesquisa é documental, qualitativa e comparativa. Mineração de textos, processamento de linguagem natural, embeddings e RAG são instrumentos para localizar, organizar e rastrear evidências; não substituem a leitura documental, a validação humana ou a interpretação da pesquisadora.

## Perguntas do RAG

Q01. Como cada país define e organiza as competências de Computação e Educação Digital em seus documentos curriculares?

Q02. De que forma o pensamento computacional é definido e incorporado ao currículo da Educação Básica?

Q03. Como os currículos tratam cidadania digital, ética digital e letramento midiático?

Q04. Como os currículos de cada país abordam competências digitais relacionadas às sete áreas do DLGF 2018?

Q05. Quais competências associadas ao século XXI aparecem nos documentos curriculares?

Q06. Como colaboração, criatividade e resolução de problemas são desenvolvidas nos currículos?

Q07. Como os documentos abordam inteligência artificial, dados, privacidade, segurança on-line e direitos digitais?

Q08. Como inclusão, acessibilidade e equidade digital aparecem nas diretrizes curriculares?

Q09. Que equilíbrio existe entre dimensões técnicas da Computação e dimensões sociais, culturais, éticas e humanas da Educação Digital?

Q10. Como os currículos articulam pensamento crítico, autonomia e participação democrática?

Q11. Como a Computação é organizada nas diferentes etapas da Educação Básica e nas áreas ou disciplinas curriculares?

Q12. Como a formação docente para Computação e Educação Digital é tratada nos documentos?

Q13. Quais eixos, conceitos e competências aparecem com maior recorrência nos currículos analisados de cada país?

Q14. Quais convergências, diferenças e lacunas aparecem entre os currículos e diretrizes oficiais dos países quanto à organização da Computação na Educação Básica e às áreas do DLGF 2018?

Q01–Q13 recuperam evidências por país. Q14 sintetiza a comparação entre países e usa somente evidências nacionais validadas. Q04 relaciona as evidências às áreas do DLGF; o framework não é currículo nacional, ranking ou escala de qualidade.

## Corpus e inclusão

O corpus analítico é formado por documentos oficiais nacionais sobre currículos e diretrizes de Computação ou Educação Digital na Educação Básica. A lista de países e documentos é definida pelo registro curado do projeto; a descoberta automática de arquivos não equivale à aprovação para análise.

Um documento só pode ser aprovado quando autoria e publicação oficial forem confirmadas; país, instituição, título, versão/ano e nível de ensino estiverem identificados; sua relação com Computação ou Educação Digital na Educação Básica estiver justificada; a versão corresponder à selecionada; páginas e extração textual forem conferidas; e proveniência, endereço oficial e decisão de inclusão estiverem registrados. Duplicatas, rascunhos, materiais jornalísticos e documentos sem relação curricular direta ficam excluídos.

Documentos pendentes, ausentes ou não registrados ficam fora do dataset validado até revisão humana. A ausência de uma fonte ou de evidência recuperada não demonstra ausência de conteúdo curricular.

## Referencial analítico

O DLGF 2018 é a única matriz internacional de competências digitais. Suas sete áreas são: operações de dispositivos e software; informação e dados; comunicação e colaboração; criação de conteúdo digital; segurança; resolução de problemas; e competências relacionadas à carreira. A tabela operacional está em `rag_project/framework/unesco_dlgf_2018.csv`.

Uma correspondência com o DLGF só é indicada quando o trecho curricular e sua página sustentarem a relação. Correspondências vagas ficam inconclusivas. O documento atualmente selecionado como referência internacional não corresponde ao DLGF 2018 e permanece excluído até a conferência da fonte correta. Nenhum outro material internacional entra no corpus ou na matriz.

## Fluxo de processamento

1. Inventariar arquivos por país e confrontá-los com o registro curado.
2. Conferir fonte oficial, versão, páginas, critérios de inclusão e status de validação.
3. Extrair diretamente PDFs pesquisáveis; aplicar OCR seletivamente a páginas sem texto ou com extração insuficiente.
4. Limpar artefatos sem alterar conteúdo substantivo e preservar marcadores de página e proveniência.
5. Gerar dataset somente com documentos nacionais aprovados e textos processados validados.
6. Criar embeddings e índice novos, separados dos índices e resultados históricos.
7. Executar Q01–Q13 por país, registrando resposta, evidência, documento, página e status.
8. Conferir cada evidência na fonte original e validar ou rejeitar os achados.
9. Produzir Q14 e a matriz DLGF somente a partir de evidências validadas.

Cada rodada recebe identificador próprio e manifesto com hashes do corpus, catálogo de perguntas, framework e parâmetros de processamento. A rodada nova não sobrescreve documentos brutos nem resultados anteriores. Chaves e credenciais ficam em configuração local ignorada pelo controle de versão e nunca são copiadas para arquivos do projeto.

## Estado da rodada

O preflight encontrou divergências entre arquivos do corpus, registro documental e status de aprovação. A geração completa do dataset e do índice permanece bloqueada até a reconciliação da curadoria e a validação da cobertura documental. Resultados de rodadas anteriores são históricos e não representam esta especificação; devem ser preservados e identificados como históricos.


