# Rodada profissional DLGF 2018 — dataset inglês validado

Esta pasta foi criada para a rodada comparativa final por competências DLGF 2018.

## Estado atual

**CONCLUÍDA — dataset inglês v2 auditado e análise final executada.**

A rodada exploratória anterior permanece separada em `run_20261015_0948` e não foi sobrescrita. Esta rodada contém 8.103 segmentos de entrada analítica, 79 documentos, 22 países e 26 competências.

## Critérios para liberar a execução

O dataset de entrada precisa:

1. ser um JSONL completo, com um registro por página/segmento;
2. conter `country`, `document_id`, `content_id`, `page_start` ou `page` e `english_text`;
3. conter texto inglês não vazio para todos os registros incluídos;
4. preservar `source_text` e a proveniência do documento original;
5. manter identificadores sem duplicidade indevida;
6. registrar o estado da tradução por documento e segmento;
7. não conter mensagens de fallback do tradutor;
8. não conter caracteres de substituição (`�`) ou erros de decodificação não revisados;
9. ter tradução integral dos documentos elegíveis, sem misturar texto original de alguns países com tradução de outros;
10. possuir hash SHA-256 e revisão/data da geração.

## Estrutura esperada após a liberação

```text
run_20261015_1033_english_validated/
├── README.md
├── run_manifest.json
├── AUDITORIA_PREVIA.md
├── input/
│   └── dataset_english.jsonl
├── audit/
│   ├── audit_records.csv
│   └── audit_summary.json
├── results/
│   ├── document_competence_hits.csv
│   ├── country_competence_summary.csv
│   └── country_competence_matrix.csv
└── imagens_por_pais/
```

## Execução realizada

O dataset foi gerado via OpenAI `gpt-4o-mini`, com temperatura `0.0`, blocos de até 6.000 caracteres, quatro trabalhadores concorrentes e cache. Foram preservados `source_text`, identificadores, páginas e proveniência; `english_text` é o campo usado na análise. Registros detectados como já ingleses foram mantidos com `translation_status=already_english`.

A análise foi executada com o codebook versionado em `../unesco_dlgf_2018_competences.csv`, revisão Git `a4126d10bedd7074ec12bcf555b99261b27b6843` e `--text-field english_text`.

## Artefatos finais

- `audit/translation_report_v2.csv`: relatório segmento a segmento;
- `results/`: CSVs, manifesto e mapa de calor da análise DLGF;
- `imagens_por_pais/`: 22 gráficos PNG, um por país.

## Conteúdo não publicado

O dataset bilíngue (`input/dataset_english_v2.jsonl`) e o cache de tradução
(`input/translation_cache.json`) permanecem apenas no ambiente local. Eles
contêm textos derivados do corpus e não são necessários para interpretar os
CSVs, gráficos e manifesto publicados nesta versão. A publicação também não
inclui os artefatos de t-SNE, PCA, distâncias ou agrupamento, explicitamente
excluídos da interpretação final.

## Disponibilização privada para avaliação

O dataset bilíngue completo pode ser disponibilizado de forma privada à banca
ou a avaliadores autorizados, mediante solicitação e controle de acesso. O
arquivo contém todos os textos originais do corpus (`source_text`), além dos
textos em inglês (`english_text`), e por isso não foi publicado no repositório
público. A disponibilização privada deve preservar as condições de acesso e os
direitos aplicáveis às fontes originais.
