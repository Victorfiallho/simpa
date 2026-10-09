# Registro de Decisões Técnicas — SIMPA

Este documento registra as ambiguidades encontradas no SRS v1.0.0 e a decisão tomada para cada uma. Ele serve de justificativa na apresentação e na documentação final (RNF05, RNF13).

Formato de cada decisão: **Problema → Opções consideradas → Decisão → Consequências**.

---

## D01 — Relação Aluno × Turma × Disciplina
- **Problema:** o aluno tem um único `turma_id`, mas as notas são lançadas por `disciplina_id`. O SRS não define o vínculo entre aluno e disciplina.
- **Opções:** (a) disciplina pertence à turma e o aluno herda as disciplinas; (b) tabela Matrícula N:N; (c) turma = oferta de disciplina.
- **Decisão:** **(b) tabela associativa N:N, chamada `Inscricao`.**
  - `Turma` = agrupamento/coorte (ex.: "IA – 2º período – Noturno").
  - `Disciplina` = oferta em um período letivo, com `turma_id` indicando a turma de origem.
  - `Inscricao(aluno_id, disciplina_id, status)` liga o aluno a cada disciplina que ele cursa.
  - `Avaliacao` e `Frequencia` referenciam `inscricao_id`, e não o par `aluno_id + disciplina_id`.
  - **Por que "Inscricao" e não "Matricula":** o SRS já usa `aluno.matricula` como o número de matrícula do aluno. Uma entidade com o mesmo nome causaria confusão no código (`matricula.matricula`?).
- **Consequências:** só é possível lançar nota para um aluno matriculado, e a integridade é garantida pelo banco. A estrutura suporta dependência ou disciplina avulsa. O `turma_id` do aluno continua existindo como turma de origem.

## D02 — Nota e frequência
- **Problema:** o RF03 mistura nota e frequência no mesmo registro, e o percentual de frequência é redundante com faltas e aulas previstas.
- **Decisão:** separar em duas entidades, `Avaliacao` (tipo, período, nota, peso) e `Frequencia` (período, aulas_previstas, faltas). O percentual é **sempre derivado** e nunca é aceito como entrada.
- **Regras adicionais:** `0 ≤ faltas ≤ aulas_previstas` e `aulas_previstas > 0`.
- **Consequências:** elimina dados contraditórios. O campo `frequencia_percentual` aparece apenas nas respostas da API.

## D03 — Perfis de acesso (RBAC)
- **Decisão:** três roles.

| Ação | Admin | Coordenador | Professor |
|---|:-:|:-:|:-:|
| Gerenciar usuários | ✔ | | |
| Cadastrar/editar alunos, turmas, disciplinas, inscrições | ✔ | ✔ | |
| Lançar/editar notas e frequência | ✔ | | ✔ (só nas suas disciplinas) |
| Consultar alunos, indicadores e risco | ✔ | ✔ | ✔ (só alunos das suas disciplinas) |
| Exportar relatórios | ✔ | ✔ | |
| Reabrir turma/disciplina encerrada | ✔ | | |

- **Consequência:** `Disciplina.professor_id` passa a ser uma FK para `Usuario`, e não mais texto livre.

## D04 — Nível do cálculo de risco
- **Problema:** um risco calculado só na média global mascara a reprovação em uma disciplina isolada.
- **Decisão:** o risco é calculado **por inscrição (aluno + disciplina)**. O status consolidado do aluno é **Em Risco se qualquer inscrição ativa estiver Em Risco**.
- **Consequência:** a justificativa cita a disciplina, a nota e a frequência (atende o RNF09). Exemplo: "POO: média 4,50 (< 6,00) — media_baixa".

## D05 — Cálculo da média
- **Média da inscrição:** média ponderada das avaliações pelo `peso`. Se todos os pesos forem iguais, o resultado coincide com a média simples.
- **Média consolidada do aluno** (só exibição): média simples das médias das inscrições ativas.
- **Frequência da inscrição:** `(Σaulas_previstas − Σfaltas) / Σaulas_previstas × 100`.

## D06 — Arredondamento e fronteira
- **Problema:** um valor de 5,996 é exibido como 6,00, mas é classificado como < 6,0.
- **Decisão:** arredondar para 2 casas (ROUND_HALF_UP) **antes** de classificar. Usar `Decimal`, não `float`.
- **Consequência:** o valor exibido sempre corresponde ao valor usado na decisão. Os testes cobrem os casos 5,994 → Em Risco e 5,995 → Sem Risco.

## D07 — Variância amostral × populacional
- **Decisão:**
  - **Populacional (÷ n):** quando o conjunto é o universo completo, ou seja, todos os alunos ativos da turma ou disciplina, sem filtro adicional.
  - **Amostral (÷ n−1):** quando a consulta aplica um filtro que forma um subconjunto (ex.: período parcial, status específico).
  - Para **n < 2** no caso amostral, o retorno é `null`, com a mensagem "amostra insuficiente".
- **Consequência:** a resposta da API informa qual modalidade foi usada (`"tipo_variancia": "populacional"`).

## D08 — Classe "Atenção" (amarelo)
- **Problema:** o RF06 prevê a cor amarela para "atenção", mas o RF07 só tem duas classes.
- **Decisão:** o RF07 continua **binário** (Em Risco / Sem Risco). "Atenção" é um **sinal visual** e não uma classe formal: aparece quando o aluno está Sem Risco, mas com média entre 6,00 e 6,99 ou frequência entre 75,00% e 79,99%.
- **Consequência:** os critérios de aceitação do RF07 continuam válidos, e o dashboard ganha uma zona de alerta preventivo.

## D09 — Aluno sem dados suficientes
- **Decisão:** uma inscrição sem avaliações ou sem registros de frequência recebe o status **"Indeterminado"** (`dados_insuficientes`), em cor azul (informação). Ela não entra na contagem de risco nem nas estatísticas.

## D10 — Turma/disciplina encerrada
- **Decisão:** com status `encerrada`, ficam bloqueados **criar, editar e excluir** avaliações, frequências e inscrições. Apenas o Admin pode reabrir, alterando o status. Encerrar uma turma bloqueia todas as disciplinas vinculadas a ela.
- **Justificativa:** o fechamento de um período letivo precisa ser imutável. Uma correção posterior exige um ato explícito e auditável.

## D11 — Quando gravar um novo `ResultadoRisco`
- **Problema:** se o risco for recalculado e gravado a cada nota ou frequência alterada, um professor que lança 30 notas em sequência gera 30 linhas de histórico quase idênticas para a mesma inscrição. O histórico fica poluído e não mostra a evolução de verdade.
- **Opções:** (a) gravar uma linha a cada recálculo; (b) manter uma linha só por inscrição e sobrescrever; (c) gravar uma linha nova apenas quando a **classificação** mudar.
- **Decisão:** **(c).** Uma linha nova é gravada quando `status`, `atencao` ou `criterios_violados` diferirem do último `ResultadoRisco` da inscrição, ou quando a inscrição ainda não tiver nenhum.
- **Consequências:** o histórico registra só as transições (ex.: Sem Risco → Em Risco em 12/10), que é o que importa para auditoria e para o RF07. A média e a frequência *atuais* continuam sendo calculadas sob demanda pelo service (princípio de dados derivados). A `media_final` e a `frequencia_final` gravadas mostram os valores no momento da transição.

---

## Princípios gerais adotados
- **Sem exclusão física** de entidades com histórico: o DELETE apenas altera o status para inativo.
- **Dados derivados** (médias, percentuais, risco) são recalculados no service sempre que uma avaliação ou frequência muda. O `ResultadoRisco` é persistido para histórico e auditoria, apenas nas mudanças de classificação (D11).
