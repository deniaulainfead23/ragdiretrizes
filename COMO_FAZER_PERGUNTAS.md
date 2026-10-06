# Como fazer perguntas novas para o RAG

## O que o RAG faz com a sua pergunta

1. Procura no corpus os trechos mais parecidos com a pergunta (12 por padrão).
2. Escreve a resposta usando só esses trechos e copia os que usou como prova.
3. Na validação, cada trecho citado é procurado no documento original.

Por isso a pergunta precisa ajudar a busca a achar os trechos certos. Uma pergunta
vaga traz trechos vagos; uma pergunta que pede o que não está escrito volta como
"o corpus não traz a informação".

## Regras práticas

- **Um assunto por pergunta.** "Como o currículo trata avaliação e formação docente?"
  divide os 12 trechos entre dois temas. Faça duas perguntas.
- **Pergunte o que os documentos dizem, não o que você conclui.** O RAG só responde
  com o que está escrito. "Como os documentos definem pensamento computacional?"
  funciona. "O currículo é adequado?" não, porque nenhum documento afirma isso.
- **Use as palavras que os documentos usam.** Se o tema tem nomes diferentes
  (cidadania digital, letramento midiático, segurança online), cite os principais.
  Para documentos em outro idioma, incluir o termo original ajuda:
  "pensamento computacional (computational thinking)".
- **Não cite país no texto se você usa pastas.** Escreva "Como os documentos
  definem…" e escolha a pasta no passo 4. A mesma pergunta serve para todas as pastas.
- **Não peça número de página.** O RagClean valida pelo conteúdo. Peça "documento e trecho".
- **Não induza a resposta.** "Por que o currículo ignora a ética?" pressupõe algo.
  Prefira "Como os documentos abordam ética no uso de tecnologias digitais?".
- **Evite "todos" e "liste tudo".** A resposta se baseia em 12 trechos, não no corpus
  inteiro. Para cobrir mais, pergunte por pasta ou aumente `RAG_MAX_TRECHOS` no `.env`.
- **Comparações amplas rendem pouco.** "Compare os 22 países" não cabe em 12 trechos.
  Faça a mesma pergunta por pasta e compare as respostas.

## Exemplos

| Evite | Prefira |
|---|---|
| Fale sobre IA. | Como os documentos abordam Inteligência Artificial no currículo: o que os estudantes devem aprender e em que etapa? |
| O currículo do Brasil é bom em inclusão? | Como inclusão, acessibilidade e equidade digital são tratadas nos documentos? *(com a pasta `brasil` selecionada)* |
| Em que página aparece programação? | Em quais etapas de ensino a programação é introduzida e com quais objetivos? Indique documento e trecho. |
| Como são tratadas avaliação, infraestrutura e formação de professores? | Três perguntas, uma para cada tema. |

## Formato do catálogo

Cada pergunta tem três campos:

| Campo | O que é | Regra |
|---|---|---|
| `id` | Código da pergunta | Único, sem espaços (ex.: `Q15`). Se ficar vazio, o sistema cria `P01`, `P02`… |
| `titulo` | Rótulo curto para o menu e os relatórios | Opcional; se vazio, usa o começo da pergunta |
| `pergunta` | Texto enviado ao RAG | Obrigatório |

O `id` é a identidade da pergunta. Importar um `id` que já existe com texto diferente
**altera** aquela pergunta; um `id` novo **acrescenta**.

## Como subir perguntas

1. Monte um arquivo com as perguntas. O mais simples é copiar
   `dados_brutos/perguntas/modelo_perguntas.csv` e abrir no Excel.
   Formatos aceitos:
   - **CSV ou XLSX** com colunas `id`, `titulo`, `pergunta` (só `pergunta` é obrigatória);
   - **TXT** com uma pergunta por linha;
   - **YAML** no formato do catálogo.
2. Salve o arquivo em `dados_brutos/perguntas/`.
3. No menu, escolha **6. Catálogo de perguntas → Importar**. O sistema confere o arquivo,
   mostra o que é novo, alterado e igual, e só grava depois da sua confirmação.
4. Escolha **7. Atualizar tudo**. Só as perguntas novas ou alteradas são enviadas ao RAG,
   e as respostas novas são validadas em seguida.

Também dá para editar `ragclean/perguntas.yaml` direto no VS Code e depois rodar o passo 7.

## O que "Atualizar tudo" refaz

| O que mudou | O que é refeito |
|---|---|
| Pergunta nova ou texto alterado | Só essa pergunta é respondida e validada |
| Documento novo, trocado ou removido do corpus | Extração e índice do que mudou; **todas** as perguntas são respondidas de novo, porque a base mudou |
| Nada | Nada; o menu avisa que está tudo em dia |

As rodadas antigas não são apagadas: ficam em `dados_derivados/respostas/` como histórico.

## Testar antes de incluir no catálogo

No passo 4, escolha "Digitar uma pergunta" para experimentar uma redação. Se a resposta
vier com trechos pertinentes, inclua a pergunta no catálogo. Se vier "o corpus não traz
a informação", reescreva com os termos que aparecem nos documentos.
