# dados_intermediarios

Gerado pelo pipeline a partir de `dados_brutos`. Pode ser apagado e refeito.

- `textos/` — texto extraído de cada documento original (passo 2).
- `manifesto.csv` — um registro por documento: caminho original, hash SHA-256, tamanho do texto, situação.
- `indice.json` — identificador do Vector Store e arquivos já enviados (passo 3).
