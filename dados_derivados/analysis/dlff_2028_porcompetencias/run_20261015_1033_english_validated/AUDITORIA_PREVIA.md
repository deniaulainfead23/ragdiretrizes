# Auditoria prévia da rodada profissional

**Data:** 15/10/2026
**Rodada:** `run_20261015_1033_english_validated`
**Status:** APROVADA E CONCLUÍDA

## Verificação realizada

A base JSONL original utilizada para construir esta rodada foi:

```text
dados_intermediarios/data/conteudos.jsonl
```

Essa base contém o campo `source_text` e foi convertida no dataset inglês v2, preservando a proveniência e criando `english_text` para a análise. A tradução foi realizada somente para os segmentos não reconhecidos como ingleses; os demais foram mantidos com `translation_status=already_english`.

Os arquivos textuais de respostas de consulta não foram usados como fonte de tradução:

```text
resposta_paises_europeus.txt
resposta_paises_europeus_dataset_inglesincompleto.txt
```

## Resultado da auditoria

- 8.103 registros JSONL válidos;
- todos os registros com `english_text` não vazio;
- `source_text`, `document_id`, página e `page_source_content_id` preservados;
- 5.113 segmentos traduzidos via API;
- 2.990 registros já em inglês mantidos;
- hash e parâmetros registrados no manifesto;
- 79 documentos nacionais reunidos em 22 países;
- 26 competências DLGF analisadas;
- 22 imagens por país validadas.

## Decisão

A rodada profissional foi liberada e concluída. A interpretação continua limitada a indicadores lexicais: as ocorrências não comprovam equivalência semântica nem desenvolvimento curricular da competência.
