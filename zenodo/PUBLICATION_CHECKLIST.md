# Checklist de publicação no Zenodo

## 1. Metadados e proveniência

- [ ] Executar `python rag_project/prepare_zenodo_dataset.py`.
- [ ] Conferir `zenodo_package/metadata/bibliographic_matrix.csv`.
- [ ] Confirmar título, instituição, ano e URL oficial de cada documento.
- [ ] Não preencher DOI, ISBN, licença ou ano por inferência quando não houver fonte verificável.
- [ ] Conferir hashes SHA-256 dos documentos usados na análise.
- [ ] Revisar registros com `source_verified=false` ou baixa confiança.

## 2. Direitos e licenças

- [ ] Revisar `zenodo_package/metadata/licensing_inventory.csv` linha a linha.
- [ ] Manter `redistribution_status=metadata_only` quando a licença do documento original for desconhecida.
- [ ] Incluir arquivo de terceiro somente quando houver permissão clara de redistribuição.
- [ ] Confirmar que CC BY 4.0 se aplica apenas aos dados e resultados produzidos pela pesquisa.

## 3. Matriz de evidências

- [ ] Abrir `evidence_matrix_candidate_for_validation.csv`.
- [ ] Excluir qualquer registro com bytes de PDF, cabeçalhos técnicos, OCR ilegível ou texto sem contexto.
- [ ] Confirmar manualmente documento, dimensão, classificação e trecho.
- [ ] Preferencialmente registrar página, seção ou unidade curricular na evidência final.
- [ ] Publicar somente registros efetivamente revisados em `evidence_matrix_validated.csv`.

## 4. Análise lexical

- [ ] Confirmar que os CSVs correspondem exatamente à execução usada na dissertação.
- [ ] Registrar versão do Python e `scikit-learn`.
- [ ] Registrar stopwords, `ngram_range`, `min_df`, `max_df`, `max_features` e `sublinear_tf`.
- [ ] Manter a nota: similaridade lexical não equivale a alinhamento curricular.
- [ ] Confirmar idioma e versão textual usada em cada análise.

## 5. Dataset comparativo

- [ ] Conferir nomes de colunas e códigos no `data_dictionary.csv`.
- [ ] Exportar também CSV aberto além do XLSX, quando possível.
- [ ] Evitar células com fórmulas dependentes de software proprietário.
- [ ] Usar UTF-8 nos CSVs.
- [ ] Remover dados pessoais que não sejam necessários à pesquisa.

## 6. Zenodo

- [ ] Reservar DOI antes do depósito final.
- [ ] Inserir DOI reservado em `CITATION.cff` e README final.
- [ ] Conferir título, autora, afiliação acadêmica quando aplicável, descrição e palavras-chave.
- [ ] Selecionar tipo **Dataset**.
- [ ] Definir versão `1.0.0`.
- [ ] Conferir licença do dataset.
- [ ] Relacionar o repositório GitHub como recurso suplementar.
- [ ] Conferir todos os arquivos antes de clicar em Publish; o registro publicado passa a ser persistente.

## 7. Referência da dissertação

Após a publicação e atribuição do DOI, incluir o dataset nas referências da dissertação e, quando pertinente, informar no capítulo metodológico que os dados derivados e metadados de proveniência foram disponibilizados em repositório aberto para favorecer transparência e reprodutibilidade.
