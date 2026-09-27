# Fluxo lógico da análise documental comparativa com RAG

## Finalidade

Este documento apresenta a lógica para analisar documentos curriculares nacionais, recuperar evidências com RAG, classificar competências digitais pelo DLGF 2018 e comparar os países.

O fluxo não produz ranking de países. O RAG localiza e organiza evidências; a interpretação final é documental, comparativa e humana.

## Regra analítica

- O DLGF 2018 é a única matriz internacional de competências digitais.
- As unidades comparativas são currículos e diretrizes oficiais nacionais de Computação e Educação Digital na Educação Básica.
- A comparação usa evidências validadas, com país, documento e página rastreáveis; não produz ranking ou escore de qualidade.

## Fluxo resumido

```text
Definir perguntas e critérios
        ↓
Selecionar países e documentos oficiais
        ↓
Preservar corpus bruto e metadados
        ↓
Extrair texto por página
        ↓
Avaliar qualidade do texto
        ↓
OCR seletivo e revisão das exceções
        ↓
Validar dataset de conteúdo
        ↓
Segmentar documentos em chunks
        ↓
Indexar chunks com metadados
        ↓
Executar perguntas Q01–Q13 por país
        ↓
Auditar respostas e evidências
        ↓
Classificar evidências pelo DLGF 2018
        ↓
Validar achados humanamente
        ↓
Consolidar perfis nacionais
        ↓
Comparar convergências e diferenças
        ↓
Gerar comparação final Q14
        ↓
Redigir resultados com rastreabilidade
```

## Etapas para o fluxograma

### 1. Definir o problema e as perguntas

**Entrada:** objetivos da pesquisa.

**Ações:**

1. Definir o que será investigado nos currículos.
2. Formular as perguntas analíticas.
3. Separar perguntas nacionais de perguntas comparativas.
4. Relacionar cada pergunta a uma categoria documental.

**Saída:** catálogo de perguntas, objetivos e categorias analíticas.

**Decisão:** a pergunta exige evidência de um país ou comparação entre países?

- País: encaminhar para Q01–Q13.
- Comparação: somente depois da validação das respostas nacionais, encaminhar para Q14.

### 2. Definir o universo e os critérios de seleção

**Entrada:** problema de pesquisa e critérios metodológicos.

**Ações:**

1. Selecionar países por representatividade continental e relevância documental.
2. Verificar a existência de documentos oficiais relacionados à Computação ou Educação Digital.
3. Registrar disponibilidade, autoria institucional, ano, idioma e fonte oficial.
4. Aplicar os critérios documentais definidos no registro curado do corpus.

**Saída:** lista de países, documentos elegíveis e documentos excluídos com justificativa.

**Decisão:** o documento é oficial, acessível, completo e relacionado ao problema?

- Sim: incluir no corpus.
- Não: registrar como excluído e não indexar.

### 3. Preservar o corpus bruto

**Entrada:** documentos coletados.

**Ações:**

1. Armazenar os arquivos originais em `dados_brutos/`.
2. Organizar documentos nacionais por país.
3. Organizar referenciais internacionais em grupo separado.
4. Não sobrescrever PDFs ou textos originais.
5. Gerar ou preservar `document_id`, caminho, hash e metadados de origem.

**Saída:** corpus bruto preservado e catálogo documental.

**Regra:** a unidade comparativa é o documento nacional; o DLGF 2018 é somente a matriz analítica externa.

### 4. Auditar os metadados

**Entrada:** catálogo documental.

**Ações:**

1. Conferir unicidade do `document_id`.
2. Conferir país ou grupo internacional.
3. Conferir título, ano, idioma, instituição e fonte.
4. Registrar função documental: currículo nacional, diretriz, lei, framework ou referência internacional.
5. Registrar status de validação e necessidade de OCR.

**Saída:** manifesto de metadados auditado.

**Decisão:** os metadados são suficientes para rastrear o documento?

- Sim: liberar para extração.
- Não: corrigir ou marcar para revisão.

### 5. Extrair o texto

**Entrada:** documentos liberados.

**Ações:**

1. Extrair texto diretamente de PDF, HTML ou TXT.
2. Preservar a separação por página quando possível.
3. Associar cada trecho ao documento e à página de origem.
4. Registrar o método de extração utilizado.

**Saída:** textos processados por página em `dados_intermediarios/`.

### 6. Avaliar a qualidade textual

**Entrada:** texto extraído.

**Ações:**

1. Contar caracteres e páginas.
2. Verificar páginas vazias ou muito curtas.
3. Verificar caracteres corrompidos e ruído de codificação.
4. Verificar a preservação da sequência de páginas.

**Saída:** classificação de qualidade por documento e página.

**Decisão:** o texto extraído é suficiente para análise?

- Sim: liberar para normalização.
- Não: encaminhar para OCR seletivo ou revisão manual.

### 7. Aplicar OCR seletivo

**Entrada:** páginas sem texto útil ou com extração insuficiente.

**Ações:**

1. Aplicar OCR somente às páginas problemáticas.
2. Selecionar o idioma adequado.
3. Preservar o número da página.
4. Comparar o resultado com a imagem original.
5. Registrar falhas, correções e intervenções manuais.

**Saída:** texto OCR revisado e relatório de exceções.

**Decisão:** o OCR produziu texto confiável?

- Sim: liberar para o dataset.
- Não: registrar como exceção, revisar manualmente ou excluir apenas a evidência não confiável.

### 8. Normalizar e organizar os textos

**Entrada:** textos extraídos e revisados.

**Ações:**

1. Corrigir quebras de linha e ruídos estruturais.
2. Remover duplicidades técnicas sem apagar conteúdo normativo.
3. Preservar o texto original em campo separado.
4. Criar, quando necessário, versão traduzida para análise multilíngue.
5. Registrar versão, método e limitações da tradução.

**Saída:** textos originais e processados, com proveniência preservada.

### 9. Validar o dataset de conteúdo

**Entrada:** textos processados.

**Ações:**

1. Verificar se cada registro é válido.
2. Conferir `document_id`, país, página e `chunk_id`.
3. Verificar ausência de textos vazios.
4. Verificar ausência de duplicidades.
5. Registrar quantidade de documentos, páginas e registros.

**Saída:** dataset liberado para indexação.

**Decisão:** todos os registros são rastreáveis e não estão vazios?

- Sim: indexar.
- Não: retornar à auditoria ou à etapa de processamento.

### 10. Segmentar os documentos em chunks

**Entrada:** dataset validado.

**Ações:**

1. Dividir os textos em unidades semanticamente coerentes.
2. Preferir páginas, seções, subseções e unidades de competência.
3. Evitar chunks excessivamente grandes ou sem contexto.
4. Preservar documento, país, página, idioma e título em cada chunk.

**Saída:** unidades textuais prontas para recuperação.

### 11. Indexar semanticamente

**Entrada:** chunks com metadados.

**Ações:**

1. Gerar embeddings dos chunks.
2. Armazenar os vetores no backend escolhido.
3. Usar o OpenAI Vector Store como backend principal quando configurado.
4. Manter FAISS como backend local ou fallback.
5. Preservar metadados para localizar documento e página.

**Saída:** índice vetorial reproduzível e consultável.

**Decisão:** o índice mantém rastreabilidade documental?

- Sim: executar perguntas.
- Não: corrigir a indexação antes de produzir resultados.

### 12. Executar as perguntas nacionais Q01–Q13

**Entrada:** pergunta analítica, país e índice vetorial.

**Ações:**

1. Executar cada pergunta separadamente para cada país.
2. Recuperar os trechos semanticamente mais relevantes.
3. Gerar uma resposta provisória baseada nos trechos recuperados.
4. Registrar pergunta, resposta, evidências, documentos e páginas.
5. Marcar respostas insuficientes como `inconclusive`.

**Saída:** respostas e evidências nacionais.

**Regra:** ausência de recuperação não significa ausência do conceito no currículo.

### 13. Auditar as respostas do RAG

**Entrada:** respostas Q01–Q13 e evidências recuperadas.

**Ações:**

1. Conferir se cada resposta responde à pergunta correta.
2. Abrir o documento original.
3. Conferir página, seção e trecho recuperado.
4. Comparar texto original e tradução, quando houver.
5. Identificar alucinação, extrapolação, duplicidade ou evidência insuficiente.
6. Corrigir o registro sem apagar a resposta automática original.

**Saída:** respostas nacionais auditadas e matriz de evidências.

### 14. Classificar as evidências pelo DLGF 2018

**Entrada:** evidências nacionais validadas documentalmente.

**Ações:**

1. Verificar se o trecho apresenta conteúdo relacionado ao letramento ou à competência digital.
2. Associar a evidência a uma ou mais áreas do DLGF 2018:
   - dispositivos e operações de software;
   - informação e literacia de dados;
   - comunicação e colaboração;
   - criação de conteúdo digital;
   - segurança;
   - resolução de problemas;
   - competências relacionadas à carreira.
3. Registrar a classificação, a justificativa e o grau de confiança.
4. Marcar correspondências vagas como inconclusivas.
5. Não transformar frequência de palavras em competência comprovada.

**Saída:** matriz de evidências classificadas pelo `DLGF_2018`.

### 15. Comparar os países

**Entrada:** evidências nacionais previamente validadas e sua classificação DLGF 2018.

**Ações:**

1. Comparar organização curricular, etapas, componentes e competências prescritas.
2. Relacionar evidências às áreas do DLGF somente quando os trechos e páginas sustentarem a correspondência.
3. Registrar convergências, diferenças e lacunas sem produzir ranking.

**Saída:** síntese Q14 e matriz comparativa entre países.

### 16. Validar humanamente os achados

**Entrada:** respostas, evidências e classificações automáticas.

**Ações:**

1. Confirmar o achado quando a evidência sustenta a afirmação.
2. Reformular a redação quando o modelo exagerar a conclusão.
3. Rejeitar achados sem suporte documental.
4. Registrar `validated`, `reformulated` ou `rejected`.
5. Associar cada achado aos IDs de evidência, documentos e páginas.

**Saída:** conjunto de achados validados para comparação.

### 17. Construir o perfil de cada país

**Entrada:** evidências e achados validados.

**Ações:**

1. Descrever como o país organiza a educação digital.
2. Identificar presença explícita, implícita, insuficiente ou não identificada.
3. Organizar os resultados pelas áreas do DLGF 2018.
4. Registrar pensamento computacional, cidadania, ética, segurança, inclusão e letramento midiático.
5. Indicar documentos e páginas que sustentam cada afirmação.

**Saída:** perfil documental validado por país.

### 18. Comparar os países

**Entrada:** perfis nacionais validados.

**Ações:**

1. Comparar convergências entre países.
2. Comparar diferenças de organização curricular.
3. Comparar ênfases técnicas, sociais, éticas e cidadãs.
4. Comparar a presença das áreas do DLGF 2018.
5. Considerar contexto, idioma, quantidade documental e nível de ensino.
6. Evitar ranking de qualidade ou superioridade curricular.

**Saída:** matriz comparativa internacional e síntese temática.

### 19. Produzir a comparação final Q14

**Entrada:** achados humanos validados das perguntas Q01–Q13.

**Ações:**

1. Construir a entrada comparativa somente com achados `validated` ou `reformulated`.
2. Associar cada convergência ou diferença às evidências nacionais.
3. Executar a Q14 como síntese comparativa.
4. Revisar a resposta final contra a matriz nacional.
5. Excluir achados rejeitados ou sem rastreabilidade.

**Saída:** comparação internacional final, pronta para interpretação.

### 20. Redigir e documentar os resultados

**Entrada:** matriz comparativa e evidências validadas.

**Ações:**

1. Apresentar o que foi encontrado por país e por eixo.
2. Distinguir evidência, síntese computacional e interpretação da pesquisadora.
3. Informar limitações de OCR, tradução, recuperação e corpus.
4. Citar documento, página e identificação da evidência.
5. Registrar versão do corpus, framework e parâmetros usados.

**Saída:** capítulo de resultados, quadros, matrizes e anexos reproduzíveis.

## Lógica das comparações

```text
Documento nacional
    ↓
Evidência recuperada
    ↓
Validação da fonte e da página
    ↓
Classificação DLGF 2018
    ↓
Perfil do país
    ↓
Comparação com outros perfis
    ↓
Convergências, diferenças e lacunas
    ↓
Interpretação da pesquisadora
```

## Produtos finais por camada

| Camada | Conteúdo | Função |
|---|---|---|
| Dados brutos | PDFs, HTML, TXT e metadados de origem | Preservar a fonte documental |
| Dados intermediários | Texto extraído, OCR, normalização, tradução, chunks e índices | Preparar a recuperação e a análise |
| Dados derivados | Respostas, evidências, classificações DLGF, matrizes, gráficos e sínteses | Produzir os resultados da pesquisa |

## Regras que devem aparecer no fluxograma

1. Documento original nunca é sobrescrito.
2. DLGF 2018 é a única matriz internacional de competências digitais.
3. RAG recupera evidências; não substitui a interpretação humana.
4. Ausência de evidência recuperada não prova ausência conceitual.
5. Toda afirmação precisa estar ligada a documento, página, trecho e país.
6. A comparação final só ocorre depois da validação por país.
7. A pesquisa não produz ranking de currículos.