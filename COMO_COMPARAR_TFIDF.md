# Como fazer a comparação TF-IDF

A comparação TF-IDF responde, com contagem de palavras, a duas perguntas diferentes.
Você escolhe qual delas ao definir a **fonte de comparação**.

| Fonte | Pergunta que responde | Use quando |
|---|---|---|
| **Lista de termos** | Onde e quanto cada termo aparece no corpus? | Você já sabe quais conceitos quer procurar (ex.: as áreas do DLGF, um conjunto de competências) |
| **Documento de referência** | Quais documentos têm o vocabulário mais parecido com o deste? | Você tem um texto-base (ex.: o PDF de um framework) e quer ver quem se aproxima dele |

Tudo roda na sua máquina, sem custo de API. O único requisito é ter feito o passo 2 (extrair o texto).

## Passo a passo

1. Salve a fonte de comparação em `dados_brutos/referencias/` (ou digite os termos na hora).
2. No menu, escolha **8. Comparação TF-IDF**.
3. **Etapa 1 — fonte:** lista de termos em arquivo, termos digitados ou documento de referência.
4. **Etapa 2 — unidade:** comparar cada documento, ou cada pasta do corpus (um resultado por país,
   se as pastas forem países).
5. **Etapa 3 — cálculo.** Os resultados vão para `dados_derivados/tfidf/<data>_<nome>/`,
   com um `LEIA-ME.md` que resume os achados e explica cada arquivo.

Cada execução cria uma pasta nova; nada é sobrescrito.

## Como montar uma lista de termos

Arquivo `.txt` ou `.csv`, uma linha por termo. A categoria é opcional:

```
categoria;termo
Segurança;privacy
Segurança;personal data
Segurança;dados pessoais
Resolução de problemas;computational thinking
Resolução de problemas;pensamento computacional
Resolução de problemas;algoritm*
```

- **Expressões valem.** `data literacy` só conta quando as duas palavras aparecem juntas.
- **`*` cobre variações.** `algoritm*` conta algoritmo, algoritmos, algorítmico.
- **Acentos e maiúsculas não importam.** `educação` e `EDUCACAO` são o mesmo termo.
- **Só palavra inteira.** `rede` não conta dentro de `prederede`; sem `*`, `rede` não conta `redes`.
- **Corpus em vários idiomas: inclua o termo em cada idioma**, na mesma categoria. A contagem é
  literal; `privacy` não encontra `privacidade`. A soma por categoria junta os idiomas.
- **Prefira termos específicos.** `digital` aparece em todo lugar e não distingue nada;
  `digital identity` distingue.
- Linhas começadas com `#` são ignoradas.

`dados_brutos/referencias/exemplo_dlgf_2018.csv` traz as sete áreas do DLGF 2018 com as
palavras-chave em inglês usadas na versão anterior do projeto. Sirva-se dele como ponto de partida.

## Como escolher um documento de referência

- Qualquer PDF, DOCX, TXT, MD ou HTML com texto (PDF escaneado não serve).
- **O idioma decide o resultado.** Um framework em inglês fica próximo dos documentos em inglês
  e distante dos demais, mesmo que tratem do mesmo assunto. Para corpus multilíngue, a lista de
  termos com traduções é mais justa.
- Se o documento também estiver no corpus, ele é retirado da comparação automaticamente.
- Palavras de ligação são ignoradas. A lista está em `ragclean/stopwords.txt` e pode ser editada.

## O que cada resultado significa

**Com lista de termos**

| Arquivo | Conteúdo |
|---|---|
| `cobertura.csv` | Quantos termos da lista cada documento/pasta contém. Comece por aqui |
| `ocorrencias.csv` | Contagem bruta de cada termo |
| `frequencia_por_10mil_palavras.csv` | Contagem descontando o tamanho do texto. Use esta para comparar |
| `tfidf.csv` | Frequência × raridade do termo no corpus. Destaca o que distingue um grupo dos outros |
| `por_categoria.csv` | Soma dos termos de cada categoria |
| `trechos_para_conferencia.csv` | O termo dentro do texto, para conferir se o sentido é o esperado |
| `mapa_de_calor.png` | Visão geral por categoria (ou por termo) |

**Com documento de referência**

| Arquivo | Conteúdo |
|---|---|
| `similaridade.csv` | Ranking de proximidade (0 a 1) e os termos em comum que explicam o valor. Comece por aqui |
| `termos_da_referencia.csv` | Os 60 termos mais fortes da referência que também aparecem no corpus, com o peso em cada documento/pasta |
| `termos_so_na_referencia.csv` | Os 40 termos mais fortes da referência ausentes do corpus: lacunas de vocabulário ou cabeçalhos repetidos |
| `similaridade.png` | O ranking em gráfico |

Os dois casos gravam também `LEIA-ME.md` (resumo) e `parametros.json` (o que foi usado, para repetir).

## Cuidados de interpretação

- **É comparação de palavras, não de significado.** Um documento pode tratar do tema com outro
  vocabulário e aparecer com valor baixo. Use `trechos_para_conferencia.csv` e o RAG (passos 4 e 5)
  para confirmar o conteúdo.
- **Valor alto não é adesão.** Vocabulário parecido não prova que o currículo adota o framework.
- **O TF-IDF depende do conjunto comparado.** Acrescentar ou retirar documentos muda os pesos.
  Compare valores só dentro da mesma execução.
- **Por pasta, o número de documentos varia.** Uma pasta com dez documentos tem mais chance de conter
  um termo do que uma com dois. As medidas por 10 mil palavras reduzem esse efeito, mas não o eliminam.
- **Termo com IDF baixo aparece em quase todos os grupos**; com IDF alto, em poucos.

## Como o cálculo é feito

- **Lista de termos:** frequência = ocorrências ÷ palavras do grupo × 10.000.
  IDF = ln((1 + N) ÷ (1 + grupos com o termo)) + 1. TF-IDF = frequência × IDF.
- **Documento de referência:** palavras e pares de palavras com três letras ou mais, sem números;
  TF sublinear (1 + ln da contagem), IDF suavizado, vetores normalizados; a similaridade é o cosseno
  entre o vetor da referência e o de cada grupo.
