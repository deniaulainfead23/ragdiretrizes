# Dados brutos

Esta camada preserva os materiais de origem da pesquisa.

## Conteúdo

- documentos curriculares e normativos oficiais;
- arquivos PDF ou equivalentes obtidos nas fontes institucionais;
- documentos de referência internacional, mantidos em grupo separado;
- manifestos de origem e registros de proveniência;
- textos originais antes de OCR, tradução, normalização ou segmentação.

## Regra de preservação

Os arquivos desta camada não devem ser sobrescritos por textos traduzidos, OCR, limpeza, normalização ou respostas produzidas pelo RAG.

Cada documento deve manter:

- identificador estável;
- país ou grupo de referência;
- título;
- instituição responsável;
- ano;
- idioma;
- endereço da fonte oficial;
- tipo documental;
- situação de acesso;
- observações de integridade.

## Organização conceitual

```text
dados_brutos/
├── corpus/
│   ├── paises/
│   └── referencias_internacionais/
└── manifestos/
```

A UNESCO, a OCDE/PISA e outros referenciais internacionais não são contabilizados como países. Eles devem permanecer identificados como referências externas ao corpus nacional.

## Compatibilidade com a rodada oficial

A rodada oficial histórica ainda registra parte dos caminhos de origem em diretórios legados. Esses caminhos permanecem documentados até que os scripts sejam atualizados e uma migração controlada seja validada. Nenhum arquivo histórico deve ser apagado durante essa transição.
