# Dados derivados

Esta camada reúne os produtos analíticos gerados a partir dos dados brutos e intermediários.

## Conteúdo

- respostas das perguntas analíticas;
- evidências recuperadas e validadas;
- matrizes por país e por pergunta;
- comparações temáticas;
- classificação das evidências segundo o referencial UNESCO/UIS 2018;
- tabelas, gráficos e relatórios de resultados;
- manifestos finais da rodada;
- registros de decisões analíticas.

## Organização conceitual

```text
dados_derivados/
├── analysis/
│   ├── official_run_YYYYMMDD/
│   ├── dlgf_2018/
│   └── comparison/
├── matrizes/
├── tabelas/
├── figuras/
└── relatorios/
```

## Regra de interpretação

Os dados derivados não substituem os documentos de origem. Cada resultado utilizado na dissertação deve manter a cadeia:

```text
resultado
→ resposta
→ evidência
→ documento
→ página ou trecho
```

A classificação `inconclusive` significa que a evidência recuperada foi insuficiente para responder à pergunta. Não significa ausência do conceito no currículo.
