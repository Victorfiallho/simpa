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
| Consultar a trilha de auditoria (`GET /auditoria`) | ✔ | ✔ | |
| Reabrir turma/disciplina encerrada | ✔ | | |

- **Consequência:** `Disciplina.professor_id` passa a guardar o id de um `Usuario`, e não mais texto livre. Como `Usuario` fica no serviço auth, esse id não é uma FK no banco (ver D13).

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

## D12 — Interface (frontend)
- **Problema:** o RF04, o RF06, o RNF11 e o RNF12 citam uma "interface", mas o SRS não define qual. O primeiro protótipo (HTML gerado a partir do Figma) foi descartado por parecer genérico: paleta roxa, slogans no lugar de títulos, caracteres no lugar de ícones e textos explicativos em excesso.
- **Decisão:** aplicação **React + Vite + TypeScript** em `frontend/`, com gráficos em Recharts, ícones Lucide e a fonte Inter. A identidade visual segue uma referência de dashboard escolhida pelo grupo: moldura escura, área de conteúdo em tom creme e quatro cores fortes.
- **Cores e status (RNF12):** as quatro cores da paleta são exatamente os quatro status, sempre acompanhadas do texto:

| Cor | Hex | Status |
|---|---|---|
| Coral | `#EA7957` | Em risco |
| Amarelo | `#E1BA58` | Atenção |
| Verde | `#8CA573` | Sem risco |
| Azul | `#7A80F0` | Indeterminado (informação) |

- **Consequências:**
  - O front fala **só com o gateway** (`/api/...`), nunca direto com um serviço.
  - Enquanto a API de indicadores não existe, as telas usam uma base de demonstração sintética e determinística (`src/dados/demonstracao.ts`), com as mesmas regras de cálculo do backend (`src/dados/calculos.ts`). Quando a API existir, a tela passa a só exibir o resultado.
  - No Docker, o front é compilado num estágio Node e servido por nginx; em desenvolvimento, `npm run dev` usa o Vite com recarga instantânea.

## D13 — Arquitetura em serviços, e não monolito
- **Problema:** a orientação do projeto pede uma arquitetura que não seja um monolito, rodando localmente com Docker.
- **Opções:** (a) monolito em camadas; (b) um microsserviço por entidade; (c) poucos serviços, divididos por responsabilidade de negócio.
- **Decisão:** **(c)**, com três serviços de backend, cada um com o próprio banco:

| Serviço | Responsabilidade | Requisitos | Tabelas |
|---|---|---|---|
| auth | login, emissão de token, usuários e perfis | RF09, D03 | `Usuario`, `LogRequisicao` |
| acadêmico | turmas, disciplinas, alunos, inscrições, notas e frequência | RF01–RF04, RF08 | `Turma`, `Disciplina`, `Aluno`, `Inscricao`, `Avaliacao`, `Frequencia` |
| analítico | indicadores, risco, gráficos e relatórios | RF05–RF07, RF11 | `ResultadoRisco` |

  - Na frente de tudo fica um **gateway nginx**, a única porta de entrada: `/api/auth`, `/api/academico`, `/api/analitico` e `/` (frontend).
  - Um único container PostgreSQL hospeda **um banco por serviço** (`auth_db`, `academico_db`, `analitico_db`). Um serviço nunca lê o banco de outro.
- **Por que não (b):** um serviço por entidade multiplicaria containers, contratos e pontos de falha sem ganho real para o tamanho do projeto.
- **Consequências:**
  - IDs que apontam para outro serviço deixam de ser FK: `Disciplina.professor_id` (auth), `ResultadoRisco.inscricao_id` (acadêmico) e `LogRequisicao.usuario_id`. A existência desses ids é conferida pela aplicação, via API.
  - Cada serviço tem as próprias migrações (Alembic), testes e `requirements.txt`, e pode ser desenvolvido por uma parte do grupo.
  - Dentro de cada serviço continua valendo a organização em camadas: `core`, `models`, `schemas`, `repositories`, `services`, `api`.

## D14 — Comunicação entre os serviços
- **Decisão:** dois tipos de comunicação.
  - **Síncrona (HTTP):** quando quem chama precisa da resposta para continuar. Ex.: o analítico busca as notas de uma inscrição em `/internal/...` no acadêmico. As rotas `/internal` são bloqueadas no gateway e só existem na rede interna do Docker.
  - **Assíncrona (eventos no RabbitMQ):** quando quem chama só precisa avisar. Ex.: ao gravar uma nota, o acadêmico publica `avaliacao.alterada {inscricao_id}` na exchange `simpa.eventos`; o worker do analítico consome e recalcula o risco (RF03, D11).
  - **Auditoria (RF12):** ao fim de cada requisição (exceto `/health` e `/internal`), cada serviço publica `log.requisicao {correlation_id, usuario_id, rota, metodo_http, status_http, ip_origem, tempo_resposta_ms, timestamp}`; o worker do auth (`auth-worker`) grava em `LogRequisicao`. Só esses campos saem do serviço: nunca corpo, cabeçalhos, query string, senha, token ou CPF (CPF no caminho é mascarado). A gravação é idempotente pelo `correlation_id` único.
- **Por que eventos no recálculo do risco:** o lançamento da nota não espera o cálculo, e se o analítico estiver fora do ar as mensagens ficam guardadas na fila até ele voltar.
- **Regras:**
  - Publicar o evento só **depois** do commit, para não anunciar algo que foi desfeito.
  - O consumidor confirma (ack) a mensagem só depois de processá-la. Se falhar, ela vai para a fila `analitico.recalculo-risco.falhas`, visível no painel do RabbitMQ.
  - O `request_id` da requisição original viaja dentro do evento, para os logs dos dois serviços poderem ser ligados (RF12).

## D15 — Tokens assinados só pelo auth (RS256 + JWKS)
- **Problema:** com uma senha compartilhada (HS256), qualquer serviço que conhece a senha também consegue emitir tokens.
- **Decisão:** o auth assina os tokens com uma **chave privada RSA** (RS256), gerada na primeira subida e guardada em um volume Docker. A chave pública fica em `/.well-known/jwks.json`; o acadêmico e o analítico a usam para validar os tokens.
- **Consequências:** só o auth emite tokens. Não há segredo de JWT para configurar no `.env`. O token leva `sub` (id do usuário), `role` (D03), `iss` e `exp`.

## D16 — PostgreSQL no lugar do SQLite
- **Problema:** o SQLite não guarda `Decimal` de verdade e não respeita a precisão de `Numeric`, o que ameaça a regra de arredondamento da D06.
- **Decisão:** PostgreSQL 17 em container, também no desenvolvimento. O SQLite fica só para testes automatizados que precisarem de banco.
- **Consequências:** `Numeric(4, 2)` para `nota`, `peso` e `media_final`; **`Numeric(5, 2)` para `frequencia_final`**, porque 100,00% tem cinco dígitos.

## D17 — Autenticação desde a Fase 1
- **Problema:** o enunciado deixa autenticação para o Marco 3, mas acrescentar o token só no fim obrigaria a reescrever todas as rotas e os testes.
- **Decisão:** todas as rotas do acadêmico exigem o token desde já. O auth tem `POST /login` e, em desenvolvimento, cria um usuário de cada perfil (`USUARIOS_DEMO=true`, senha `DEMO_SENHA` do `.env`). Das regras de perfil da D03, só "reabrir o que está encerrado" já é aplicada (D10); as demais entram na Fase 3.
- **Consequência:** a Fase 3 só acrescenta as regras de permissão por perfil, sem mexer no contrato das rotas.

## D18 — Contrato de dados da API
- **Decimais como texto:** notas, pesos e percentuais saem como texto (`"7.50"`, `"78.13"`), não como número de ponto flutuante. Assim o valor que chega ao cliente é exatamente o do banco (D06). A entrada aceita número ou texto, com no máximo 2 casas.
- **CPF mascarado:** a API devolve só os dígitos do meio (`***.982.247-**`). O CPF completo nunca sai do serviço acadêmico (RNF04).
- **Exclusão:** `DELETE` de turma, disciplina, aluno e inscrição é lógico (muda o status). Já uma nota ou frequência lançada por engano é apagada de fato, porque não tem histórico próprio, mas só enquanto a disciplina está aberta (D10). O histórico de risco fica no `ResultadoRisco` (D11).
- **Erros:** todo erro traz um código interno estável, catalogado em [`codigos-erro.md`](codigos-erro.md).

## D19 — Situação consolidada do aluno
- **Problema:** a D04 diz quando o aluno está Em Risco, mas não diz o que acontece quando ele tem uma disciplina sem dados (D09) e as outras sem risco.
- **Decisão:** o aluno fica **Em risco** se qualquer inscrição estiver em risco. Senão, inscrições sem dados são ignoradas e ele fica **Sem risco** (com o sinal de **Atenção** se alguma disciplina estiver na faixa da D08). Só fica **Indeterminado** se nenhuma inscrição tiver dados suficientes.
- **Quais inscrições contam:** ativas e concluídas. Trancadas e canceladas ficam fora do risco e dos indicadores.
- **Na tela e nos relatórios:** a API devolve `status` (classe formal do RF07) e `atencao` (sinal da D08), e também `situacao`, que junta os dois nas quatro categorias visuais: Em risco, Atenção, Sem risco e Indeterminado.

## D20 — Onde os indicadores são calculados
- **Decisão:** o analítico não guarda cópia das notas. A cada consulta, busca as inscrições do recorte na rota interna do acadêmico (`/internal/inscricoes`) e calcula tudo na hora, em funções puras com `Decimal`. Só o histórico de risco é persistido (`ResultadoRisco`, D11).
- **Recálculo do risco:** o worker recebe cada evento do acadêmico, recalcula a inscrição e grava uma linha nova só se a classificação mudou. O comando `python -m app.comandos.recalcular` faz o mesmo para todas as inscrições de uma vez.
- **Painel:** a interface usa uma rota única, `GET /painel`, que entrega indicadores, situação por aluno e os dados dos gráficos. Isso evita várias chamadas por tela.
- **Consequências:** os números são sempre os atuais, sem risco de ficarem desatualizados. O custo é uma chamada HTTP ao acadêmico por consulta, o que é irrelevante no tamanho do projeto. Se crescer, o caminho é guardar um resumo por inscrição no analítico, atualizado pelos mesmos eventos.

## D21 — Nível 2: interpretação, predição e recomendação
- **Decisão:** o SIMPA vai além da estatística descritiva com três recursos, todos no serviço analítico:
  - **Interpretação automática** (`services/interpretacao.py`): regras que transformam os indicadores em achados escritos. Elas dizem quantos alunos estão em risco, se o risco vem de nota ou de falta, qual disciplina concentra o risco, onde a média caiu ou subiu da N1 para o acumulado, a força da correlação frequência × nota e se a turma é homogênea.
  - **Predição por regressão linear múltipla** (`services/predicao.py`): `N2 = b0 + b1·N1 + b2·frequência_N1`. O ajuste é por mínimos quadrados com as equações normais em forma matricial, `β = (XᵀX)⁻¹Xᵀy`, usando `numpy`; é a ligação com Álgebra Linear. Com a N2 estimada, o sistema projeta a média final e o risco de cada inscrição.
  - **Recomendações heurísticas** (`services/recomendacoes.py`): cada critério gera uma ação sugerida, com prioridade. Média baixa sugere monitoria; frequência baixa, contato da coordenação; risco em duas ou mais disciplinas, conversa sobre a carga do semestre; projeção de queda, acompanhamento preventivo.
- **Validação:** o erro do modelo é medido por validação cruzada "deixa um de fora", calculada pela matriz de projeção `H = X(XᵀX)⁻¹Xᵀ` (resíduo sem a observação i = eᵢ / (1 − hᵢᵢ)). Assim o erro informado não fica otimista. O sistema também mede quantas vezes a projeção acerta a situação final de risco.
- **Por que float aqui:** a regressão é uma estimativa e roda em `float` (numpy). A classificação oficial do RF07 continua em `Decimal` (D06) e não depende da predição.
- **Limites, mostrados na tela:** é associação, não causa; a amostra é pequena e sintética; inscrições do mesmo aluno não são independentes; a projeção apoia o acompanhamento, mas não substitui a classificação oficial.

---

## Princípios gerais adotados
- **Sem exclusão física** de entidades com histórico: o DELETE apenas altera o status para inativo.
- **Dados derivados** (médias, percentuais, risco) são recalculados no service sempre que uma avaliação ou frequência muda. O `ResultadoRisco` é persistido para histórico e auditoria, apenas nas mudanças de classificação (D11).
- **Uma transação por caso de uso:** os repositórios só fazem `add`/`flush`; o service chama `commit()` uma única vez, no fim. Se algo falhar antes, nada é gravado.
- **Cálculos em funções puras:** estatística e risco recebem números e devolvem resultados, sem banco nem rede, para serem testados com valores calculados à mão.
