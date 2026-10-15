# Protocolo reutilizável de auditoria e validação textual

## 1. Objetivo

Este protocolo descreve um procedimento reprodutível para auditar, validar e liberar documentos textuais destinados a recuperação semântica, RAG, mineração de textos e análise documental multilíngue.

O método foi consolidado a partir das rotinas empregadas no projeto `ragdiretrizes`, incluindo auditoria de metadados, inspeção de extração textual, OCR seletivo, verificação por página, revisão visual de exceções, validação estrutural do dataset e preservação de rastreabilidade.

O protocolo foi desenhado para ser reutilizado por outros pesquisadores sem depender do corpus original.

## 2. Princípios

1. **Preservar a fonte original.** O PDF, HTML ou outro documento de origem não deve ser sobrescrito durante OCR, limpeza ou normalização.
2. **Separar fonte de derivado.** Arquivos processados, OCR e datasets devem ser gravados em caminhos próprios.
3. **Manter identificador persistente.** Cada documento recebe um `document_id` único e estável.
4. **Preservar a página.** Todo trecho usado como evidência deve permanecer vinculado ao documento e à página de origem.
5. **Automação não substitui revisão humana.** Métricas detectam páginas suspeitas; a decisão final sobre exceções é humana.
6. **Página vazia não é falha automaticamente.** Sumários, separadores, páginas em branco e elementos gráficos precisam ser distinguidos de falhas de OCR.
7. **Texto original e tradução são campos distintos.** Em corpus multilíngue, o texto original deve ser preservado; traduções servem à leitura e análise, não substituem a fonte.
8. **Ausência de recuperação não prova ausência conceitual.** Falha de busca semântica não deve ser convertida automaticamente em conclusão analítica.

## 3. Artefatos mínimos

O fluxo recomenda quatro artefatos:

- `metadata/documentos.csv`: catálogo mestre das fontes;
- `metadata/processed_documents.csv`: manifesto dos textos liberados;
- textos processados com marcadores `## PAGE n`;
- `data/conteudos.jsonl`: dataset derivado com `document_id`, página e texto.

Relatórios de auditoria devem ser armazenados separadamente, por exemplo em `analysis/audit/`.

## 4. Etapa A — Inventário e auditoria de metadados

Verificar:

- existência de `document_id`;
- unicidade do identificador;
- título, ano e idioma quando disponíveis;
- `source_scope`;
- país ou referência internacional;
- caminho da fonte;
- status de validação;
- grupo ou classificação de auditoria;
- necessidade de OCR;
- observações estruturais.

### Regra de escopo

Para fontes nacionais:

```text
source_scope = national
country = <país>
```

Para UNESCO, OCDE/PISA ou outros referenciais internacionais:

```text
source_scope = international_reference
country = vazio
framework_source = <organização ou framework>
```

Referências internacionais não devem ser tratadas como países na análise comparativa.

## 5. Etapa B — Inspeção do texto extraído

Antes de aplicar OCR, testar a extração direta. Para cada página, observar pelo menos:

- número de caracteres;
- proporção de caracteres alfanuméricos;
- presença de caracteres de substituição (`�`);
- páginas totalmente vazias;
- páginas extremamente curtas;
- ruído recorrente ou codificação quebrada;
- preservação da sequência de páginas.

No projeto, uma heurística útil para triagem foi:

```python
if n == 0:
    status = "EMPTY"
elif n < 40:
    status = "LOW_TEXT"
elif alnum_ratio < 0.25:
    status = "LOW_QUALITY"
else:
    status = "OK"
```

Esses limiares servem para **triagem**, não como critério científico absoluto. Em outros corpora, devem ser calibrados.

## 6. Etapa C — OCR seletivo

OCR deve ser aplicado somente quando a extração direta for insuficiente.

Procedimento recomendado:

1. identificar o documento e idioma;
2. renderizar cada página em resolução adequada;
3. executar OCR com pacote de idioma apropriado;
4. limpar apenas artefatos triviais de espaçamento;
5. preservar o texto por página;
6. registrar métricas de qualidade;
7. gerar um arquivo Markdown com `## PAGE n`;
8. gerar CSV de validação por página.

Exemplo de configuração Tesseract usada no projeto:

```python
pytesseract.image_to_string(
    image,
    lang="chi_sim+eng",
    config="--oem 1 --psm 6"
)
```

O idioma deve ser adaptado ao documento.

## 7. Etapa D — Revisão das páginas problemáticas

Páginas classificadas como `EMPTY`, `LOW_TEXT` ou `LOW_QUALITY` devem ser revisadas visualmente.

Para cada exceção, registrar uma das decisões:

- **página vazia confirmada**;
- **texto curto legítimo**;
- **sumário ou página estrutural**;
- **OCR aceitável após nova tentativa**;
- **transcrição manual validada visualmente**;
- **falha não resolvida**.

### Transcrição manual

Quando uma página for claramente legível visualmente, mas o OCR falhar por diagramação, linhas pontilhadas, tabelas ou outro artefato, uma transcrição manual pode ser usada desde que:

- a página seja identificada;
- o original permaneça preservado;
- a decisão seja registrada;
- a transcrição não introduza conteúdo interpretativo;
- a revisão seja visualmente conferida.

## 8. Etapa E — Manifesto de processamento

O manifesto deve registrar, no mínimo:

```text
document_id
status
processed_path
pages_extracted
notes
```

Status recomendados:

```text
ready
ready_with_structural_warning
ready_ocr
ready_ocr_with_page_exception
```

Somente documentos explicitamente liberados devem seguir para indexação.

## 9. Etapa F — Validação do dataset de conteúdo

Antes da indexação, verificar:

- cada linha é JSON válido;
- número de registros;
- número de documentos únicos;
- unicidade de `content_id`;
- ausência de textos vazios;
- existência de `document_id` e página;
- inexistência de duplicatas.

Exemplo:

```python
import json
from pathlib import Path

rows = [
    json.loads(x)
    for x in Path("data/conteudos.jsonl").read_text(encoding="utf-8").splitlines()
    if x.strip()
]

print("Registros:", len(rows))
print("Documentos únicos:", len(set(r["document_id"] for r in rows)))
print("content_id únicos:", len(set(r["content_id"] for r in rows)))
print("IDs duplicados:", len(rows) - len(set(r["content_id"] for r in rows)))
print("Textos vazios:", sum(not str(r.get("source_text", "")).strip() for r in rows))
```

## 10. Etapa G — Critérios de liberação

Um documento pode ser liberado quando:

- possui identificador único;
- possui classificação de escopo coerente;
- o arquivo processado existe;
- a sequência de páginas está preservada;
- páginas suspeitas foram revisadas;
- exceções estão registradas;
- a qualidade é suficiente para recuperação textual;
- a fonte original continua disponível;
- o vínculo `document_id -> página -> trecho` permanece rastreável.

## 11. Validação de evidências em RAG multilíngue

Após a recuperação semântica, cada evidência deve conter:

```text
evidence_id
question_id
country
document_id
page_start
page_end
source_language
source_text
translated_text_pt
translation_status
validation_status
```

O campo `source_text` é a evidência primária. A tradução serve para leitura e síntese em português.

A resposta automática deve começar como `candidate` ou `inconclusive`. O status `validated` deve ser atribuído somente depois de revisão humana.

## 12. Técnica de revisão rápida reutilizável

Para reduzir tempo em novos corpora:

1. rode primeiro a auditoria automática completa;
2. filtre apenas páginas com status diferente de `OK`;
3. revise visualmente somente as exceções;
4. registre a decisão diretamente no manifesto ou CSV de validação;
5. regenere o dataset derivado;
6. execute a validação estrutural novamente;
7. só então indexe.

Isso transforma a revisão humana de um processo integral para um processo **orientado por exceções**, mantendo rastreabilidade e reduzindo esforço.

## 13. Implementação neste repositório

### Local ou VS Code

```bash
python -m rag_project.audit_corpus --all
```

Saídas:

```text
analysis/audit/audit_summary.json
analysis/audit/processed_page_audit.csv
```

### Google Colab

Abra:

```text
Auditoria_Reutilizavel_Corpus_RAG.ipynb
```

O notebook inclui instalação, Drive, auditoria consolidada, OCR seletivo, revisão visual e validação do JSONL.

O notebook histórico `OCR_Seletivo_Corpus_RAG.ipynb` permanece preservado como evidência do procedimento específico utilizado nos documentos que exigiram OCR.

## 14. Registro do processo aplicado ao corpus deste projeto

Na consolidação final da auditoria do projeto foram catalogados 86 documentos. A distribuição final dos grupos de auditoria foi:

```text
Grupo A: 61
Grupo B: 20
Grupo C: 3
Grupo D: 2
```

Após processamento e revisão, o manifesto de textos foi consolidado em:

```text
ready: 81
ready_ocr: 2
ready_ocr_with_page_exception: 1
ready_with_structural_warning: 2
```

O corpus liberado preservou 79 documentos de escopo nacional e 7 referências internacionais.

O dataset de conteúdo validado resultou em:

```text
Registros: 8099
Documentos únicos: 86
content_id únicos: 8099
IDs duplicados: 0
Textos vazios: 0
```

Esses valores documentam a execução realizada neste projeto; não são parâmetros obrigatórios para reutilizações futuras.

## 15. Reprodutibilidade

Para possibilitar auditoria por terceiros, recomenda-se versionar:

- scripts;
- notebooks;
- parâmetros;
- metadados;
- manifestos;
- relatórios de auditoria;
- decisões sobre exceções;
- versões das perguntas e prompts analíticos.

Arquivos originais muito grandes podem permanecer em armazenamento externo, desde que o catálogo mantenha identificadores, caminhos e referências de origem suficientes para reconstrução do processo.
