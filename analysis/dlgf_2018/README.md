# Análise UNESCO/UIS DLGF 2018

Este diretório é reservado aos artefatos produzidos pela camada analítica baseada no `UNESCO_DLGF_2018`.

Arquivos esperados após a execução de `python rag_project/classify_dlgf_evidence.py`:

- `dlgf_evidence_mapping.csv`: classificação de cada evidência preservando proveniência e status de validação.
- `dlgf_summary_country_area.csv`: resumo descritivo de evidências por país e área DLGF.
- `dlgf_country_area_matrix.csv`: matriz país × área DLGF.
- `dlgf_country_area_matrix.png`: visualização descritiva da matriz, quando matplotlib/pandas estiverem disponíveis.

## Regra de interpretação

As contagens são indicadores de evidências recuperadas e classificadas. Não medem qualidade curricular, superioridade entre países, desempenho educacional ou implementação efetiva. Ausência de evidência recuperada deve ser tratada como `not_detected` ou inconclusiva, nunca como prova de ausência conceitual.
