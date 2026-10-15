# Rodada oficial RAG — 12/09/2026

Documento de fechamento da rodada oficial do pipeline RAG.

## Resultado técnico final

- 22 países
- 286 respostas Q01–Q13
- 283 respostas `candidate`
- 3 respostas `inconclusive`
- 626 evidências
- `q14_input.csv`: 286 linhas
- `q14_by_question.csv`: 13 comparações temáticas
- Q14 final gerada
- 0 problemas estruturais no fechamento

## Fluxo executado

1. Auditoria do corpus e metadados.
2. Extração direta de texto quando possível.
3. OCR seletivo somente para exceções.
4. Validação por página e correção das exceções.
5. Construção de `data/conteudos.jsonl` com 8.099 registros e 86 documentos.
6. Indexação de 86 documentos no OpenAI Vector Store.
7. Execução das perguntas Q01–Q13 por país.
8. Reparação de evidências históricas com documento/página ausentes.
9. Auditoria estrutural da rodada oficial.
10. Construção da base consolidada da Q14.
11. Geração das 13 comparações temáticas.
12. Geração da síntese comparativa Q14.
13. Fechamento técnico final com manifesto.

## Regra metodológica central

A ausência de recuperação semântica não deve ser interpretada como ausência conceitual no currículo ou no sistema educacional do país. Resultados `inconclusive` representam insuficiência de evidência recuperada para a pergunta analisada.

## Próxima etapa

A rodada está tecnicamente fechada. A etapa seguinte é a análise científica e validação semântica das respostas Q01–Q13 e, posteriormente, a consolidação comparativa da Q14.
