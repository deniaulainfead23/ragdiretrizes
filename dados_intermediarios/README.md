# Dados intermediários

Esta camada reúne os materiais produzidos durante o processamento do corpus. Eles não são fontes originais e ainda não constituem os resultados finais da pesquisa.

## Conteúdo

- metadados normalizados;
- textos extraídos;
- textos submetidos a OCR seletivo;
- traduções de apoio;
- textos segmentados em páginas e trechos;
- datasets JSONL utilizados na indexação;
- saídas exploratórias de frequência, TF-IDF e similaridade;
- logs de processamento e auditoria;
- registros de revisão humana.

## Organização conceitual

```text
dados_intermediarios/
├── metadata/
├── processed/
├── processed_ocr/
├── traducoes/
├── datasets/
├── analise_lexical/
└── auditoria/
```

## Regras

1. O texto original deve permanecer preservado em dados brutos.
2. Toda transformação deve registrar origem, versão, data e ferramenta.
3. OCR e tradução devem ser identificados como mediações metodológicas.
4. Um dado intermediário não deve ser apresentado como evidência final sem conferência no documento original.
5. Os identificadores `document_id`, `content_id`, `chunk_id` e página devem ser mantidos.

A ausência de texto em uma saída intermediária deve gerar revisão ou registro de exceção. Não deve ser interpretada diretamente como ausência do tema no documento.
