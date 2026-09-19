# Análise UNESCO/UIS DLGF 2018

Este diretório reúne os artefatos produzidos pela camada analítica baseada no
framework `UNESCO_DLGF_2018`.

Arquivos esperados após a execução de `python rag_project/classify_dlgf_evidence.py`:

- `dlgf_evidence_mapping.csv`: classificação das evidências com proveniência e status;
- `dlgf_summary_country_area.csv`: resumo por país e área DLGF;
- `dlgf_country_area_matrix.csv`: matriz país por área DLGF;
- `dlgf_country_area_matrix.png`: visualização descritiva, quando disponível.

As contagens são indicadores de evidências recuperadas e classificadas. Não
medem qualidade curricular, superioridade entre países, desempenho educacional
ou implementação efetiva. Ausência de evidência recuperada deve ser tratada
como `not_detected` ou inconclusiva, nunca como prova de ausência conceitual.