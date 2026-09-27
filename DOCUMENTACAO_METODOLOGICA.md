# Documentação metodológica da comparação curricular com RAG

## 1. Objetivo e escopo

A pesquisa compara como currículos e diretrizes oficiais dos países tratam a Computação e a Educação Digital na Educação Básica. A unidade de análise é o documento oficial nacional, interpretado em seu contexto institucional e escolar. A comparação identifica convergências, diferenças e lacunas sem estabelecer rankings de países ou juízos de qualidade curricular.

O único referencial internacional utilizado como matriz analítica de competências digitais é o Digital Literacy Global Framework (DLGF), publicado em 2018. A comparação tem dois eixos: entre os documentos e países do corpus, e entre as evidências curriculares e as áreas do DLGF 2018. O DLGF não é considerado currículo nacional nem unidade-país.

A investigação é documental, qualitativa e comparativa. Processamento de linguagem natural, mineração textual, embeddings e RAG apoiam a localização e organização das evidências, mas não substituem análise humana.

## 2. Perguntas de pesquisa e uso do RAG

O catálogo ativo contém 14 perguntas em `rag_project/questions/questions.yaml`. Q01–Q13 recuperam evidências por país; Q14 compara os países somente após a validação das evidências. Q04 organiza evidências nacionais segundo as sete áreas do DLGF 2018. Não há pergunta adicional de classificação.

As respostas devem preservar `question_id`, país, `document_id`, título, página, trecho original, `evidence_id` e status de validação. A ausência de trecho recuperado significa apenas que a busca não identificou evidência suficiente; não comprova ausência do tema no currículo.

## 3. Delimitação do corpus

O corpus principal compreende documentos oficiais de países, relacionados à Computação ou à Educação Digital na Educação Básica. O registro curado em `rag_project/config/corpus_registry.yaml` é a lista controlada de inclusão; arquivos descobertos em pastas não são aprovados automaticamente.

A inclusão exige confirmação da autoria institucional e da publicação oficial, pertinência ao nível de ensino e ao tema, versão/ano identificáveis, texto acessível e rastreabilidade para a fonte oficial. Duplicatas, rascunhos, material jornalístico e documentos fora do escopo são excluídos. Para cada documento devem ser registrados país, instituição, título, versão/ano, idioma, caminho, hash, fonte oficial, páginas, papel documental e status de validação.

O número de páginas deve ser extraído do arquivo real, nunca preenchido por valor padrão. Documentos com layout complexo, páginas ausentes ou extração duvidosa exigem conferência humana. OCR é seletivo: primeiro tenta-se extração textual direta; OCR é usado apenas em páginas sem texto ou com extração insuficiente. A qualidade do texto processado é registrada por página.

## 4. Preparação e dataset

O pipeline cria inventário e preflight antes de construir artefatos. A etapa bloqueia a geração quando encontra arquivos ausentes no registro, arquivos nacionais ainda sem metadados ou documentos pendentes de aprovação.

O dataset de análise contém somente documentos de escopo nacional com `validation_status=validated` e texto processado em status liberado. Referenciais e outros materiais internacionais não são misturados ao dataset curricular. O texto original e os marcadores de página são preservados; a limpeza remove apenas ruído de extração e mantém a proveniência.

Cada rodada recebe um identificador próprio, manifesto com hashes do corpus, catálogo de perguntas e framework, e diretório de saída novo. Datasets, índices e respostas antigos não são sobrescritos. Credenciais de API permanecem em configuração local ignorada pelo Git e não são copiadas para arquivos versionados.

## 5. Matriz DLGF 2018

A matriz operacional está em `rag_project/framework/unesco_dlgf_2018.csv`, com o identificador técnico `DLGF_2018`. As sete áreas são: operações de dispositivos e software; informação e dados; comunicação e colaboração; criação de conteúdo digital; segurança; resolução de problemas; e competências relacionadas à carreira.

A associação entre evidência curricular e área do DLGF exige suporte explícito ou semanticamente justificável no trecho e na página citada. Correspondências ambíguas ficam como inconclusivas. Contagens são descritivas e não medem qualidade, implementação, desempenho ou superioridade entre países.

## 6. Execução e validação

1. Auditar o corpus e reconciliar arquivos com o registro curado.
2. Verificar fonte, versão, país, páginas, pertinência e status de cada documento.
3. Processar texto e OCR seletivo, revisar páginas problemáticas e gerar dataset validado.
4. Criar embeddings e índice local novo a partir do dataset validado.
5. Executar Q01–Q13 para cada país coberto e salvar respostas e evidências na pasta da rodada.
6. Conferir cada trecho e página na fonte original; validar, reformular ou rejeitar cada achado.
7. Gerar matriz DLGF 2018 e Q14 somente a partir de evidências validadas.

A síntese automática é ponto de partida, não resultado científico final. Toda afirmação comparativa deve ser rastreável às fontes nacionais originais.

## 7. Estado e limitações da rodada

O preflight atual identificou divergências entre o corpus local, o registro documental e os status de aprovação. A geração completa do dataset, do índice, das respostas e da comparação está bloqueada até concluir a curadoria e a validação da cobertura. Uma execução parcial não deve ser apresentada como se representasse todos os países.

Resultados de rodadas anteriores permanecem preservados como históricos e não devem ser combinados com a nova rodada. A análise descreve prescrições documentais e não permite, por si só, concluir como o currículo é implementado nas escolas.
