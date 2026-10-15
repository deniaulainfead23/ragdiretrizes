# Pacote de publicação no Zenodo

Este diretório organiza os produtos de dados derivados da pesquisa para depósito público e reprodutível no Zenodo.

## Escopo recomendado

O depósito deve priorizar **dados produzidos pela pesquisa** e **metadados de proveniência**. PDFs e outros documentos oficiais de terceiros não devem ser redistribuídos automaticamente. Para esses materiais, registrar URL oficial, instituição, data de acesso, hash SHA-256 e situação de licença/redistribuição.

## Estrutura sugerida do depósito

```text
zenodo_package/
├── README.md
├── CITATION.cff
├── LICENSE_DATA.txt
├── data_dictionary.csv
├── metadata/
│   ├── bibliographic_matrix.csv
│   ├── source_registry.csv
│   ├── document_checksums.csv
│   └── licensing_inventory.csv
├── comparative_dataset/
│   ├── curriculum_comparative_dataset.csv
│   └── curriculum_comparative_dataset.xlsx
├── lexical_analysis/
│   ├── lexical_document_tfidf.csv
│   ├── lexical_document_top_terms.csv
│   ├── lexical_group_tfidf.csv
│   ├── lexical_group_frequency.csv
│   ├── lexical_group_similarity.csv
│   ├── lexical_group_similarity_matrix.csv
│   ├── lexical_country_similarity_ranking.csv
│   └── analysis_summary.json
├── evidence/
│   ├── evidence_matrix_candidate_for_validation.csv
│   └── evidence_matrix_validated.csv
└── methodology/
    ├── methodology.md
    └── provenance.md
```

## Regras de publicação

1. **Não publicar automaticamente PDFs de terceiros.** A disponibilidade pública de um documento não implica autorização para redistribuição.
2. **Publicar metadados e resultados derivados**, como TF-IDF, frequências, matrizes de similaridade, classificações e registros de proveniência.
3. **Preservar rastreabilidade**, usando `document_id`, título, país, instituição, URL oficial e hash SHA-256.
4. **Separar evidência validada de evidência automática.** Registros gerados por fallback, OCR defeituoso ou texto binário de PDF não devem entrar na versão validada.
5. **Não interpretar similaridade lexical como alinhamento curricular.** TF-IDF e similaridade cosseno são ferramentas exploratórias.
6. **Manter versão do dataset.** Recomenda-se iniciar com `v1.0.0` e registrar alterações posteriores no Zenodo.

## Título sugerido

**Comparative Dataset of Computing, Digital Education and Digital Citizenship Curricula in Basic Education**

## Descrição sugerida

This dataset supports a comparative study of official curriculum documents related to Computing, Digital Education, Computational Thinking and Digital Citizenship in Basic Education. It contains bibliographic and provenance metadata, analytical classifications, lexical indicators derived through TF-IDF and cosine similarity, and validated documentary evidence organized by country and analytical dimension. The dataset was developed within a comparative education and digital humanities research framework combining documentary analysis, natural language processing and Retrieval-Augmented Generation (RAG). Original third-party curriculum documents are referenced through their official institutional sources and persistent checksums and are not redistributed unless their licensing conditions explicitly permit redistribution.

## Palavras-chave sugeridas

`digital education`; `computational thinking`; `computing education`; `digital citizenship`; `comparative education`; `curriculum`; `natural language processing`; `digital humanities`; `RAG`.

## Tipo de recurso

- Dataset principal: **Dataset**
- Pipeline computacional: **Software**

## Licenciamento

Para os dados originais produzidos pela pesquisa, a licença sugerida é **Creative Commons Attribution 4.0 International (CC BY 4.0)**. A licença não deve ser aplicada a documentos de terceiros cujo direito de redistribuição não tenha sido confirmado.

## DOI

Antes da publicação final, reserve o DOI no Zenodo e preencha o identificador em `CITATION.cff`, `.zenodo.json` e na versão final deste README.

## Preparação automática

Execute:

```bash
python rag_project/prepare_zenodo_dataset.py
```

O script cria `zenodo_package/` sem modificar o corpus original. Os arquivos de evidência permanecem sujeitos à revisão humana antes do depósito final.
