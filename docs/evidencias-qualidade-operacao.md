# Evidências: testes entre serviços, interface, filas e recuperação

Registro de execução do guia `plano-execucao-qualidade-operacao.md` (10/11/2026). Só entra aqui o que foi executado e conferido. Nada neste arquivo contém credenciais.

## Estado de partida (etapa 2)

| Item | Resultado |
|---|---|
| Commit analisado | `1b702c6e9856ff6cfddee61baf0a43f592be31a0` (`feat(front): telas de cadastros e lançamento de notas e frequência`) |
| Alterações locais antes de começar | Nenhuma (`git status --short` vazio) |
| Remotos | `origin` = `mariojorgeb/simpa-projeto`; `grupo` = `Victorfiallho/simpa`. O trabalho vai para a branch `claude/dazzling-galileo-q87j8b` do `grupo` |
| `AGENTS.md` | Nenhum no repositório (busca com `find`; o `rg` não está instalado) |
| Ambiente | Contêiner Linux. Docker 29.9.2, Compose v5.6.1, Python 3.13.18, Node 22.23.4, npm 10.9.9 |
| Docker | O daemon não estava ativo; foi iniciado à mão com `dockerd`. As imagens base vêm do Docker Hub e o limite de requisições (429) obriga a repetir o `pull` |
| Build de imagens | O proxy do ambiente bloqueia `pip` e `npm` dentro do build. Contorno usado: Dockerfiles temporários fora do repositório, `network: host` e o CA do proxy montado só no build |
| Arquivos do plano que já existiam | Nenhum: `compose.test.yml`, `tests/integration/`, `scripts/backup/`, `infra/monitoramento/` e Playwright **não existem** |
| Diferença para a análise do guia | O guia cita o commit `233326d` do grupo e a cópia local em `06917a3`. A branch atual (`1b702c6`) tem as telas de cadastro e lançamento, a matriz de rastreabilidade e os índices compostos |

### Contratos revisados

- **CI** (`.github/workflows/ci.yml`): três jobs, backend (ruff, formatação e testes por serviço com cobertura mínima de 80%), frontend (`npm ci` e build) e imagens Docker.
- **Publicação de eventos** (`services/academico/app/events/publicador.py`): publica **depois do commit**, abrindo uma conexão nova a cada evento, **sem confirmação do broker** e sem outbox. Se o RabbitMQ estiver fora, `publicar_sem_falhar` só registra o erro. O próprio código lista o outbox como melhoria futura.
- **Consumo** (`services/analitico/app/events/consumidor.py`): fila durável `analitico.recalculo-risco`, `prefetch_count=1`, `ack` só depois de processar. Em falha, `nack` sem reenfileirar leva a mensagem para a fila de falhas por dead-letter. **Não há tentativas, espera progressiva nem idempotência por identificador de evento**: o envelope não tem `event_id`.
- **Topologia**: a fila e as ligações são declaradas pelo worker ao iniciar; o publicador só declara a exchange. Pela leitura do código (ainda não reproduzido em teste), um evento publicado antes de existir fila ligada não tem destino, e o publicador não usa `mandatory` nem confirmação, então ele se perde sem erro.

## O que foi feito

### Falha encontrada e corrigida: vazamento na consulta integrada do aluno (etapa 4.3)

**Sintoma.** `GET /alunos/{id}` e `GET /alunos/matricula/{matricula}` só conferiam se o aluno tinha *alguma* inscrição em uma disciplina do professor. Passando nessa checagem, devolviam **todas** as inscrições do aluno, com notas e frequências lançadas por outros professores, o que contraria a D03.

**Reprodução.** Teste de regressão `test_consulta_integrada_do_aluno_nao_vaza_a_disciplina_de_outro_professor` (`services/academico/tests/test_rbac.py`): um aluno inscrito em duas disciplinas, cada uma de um professor, com notas e frequências nas duas.

| Situação | Resultado |
|---|---|
| Sem a correção | Falha: o professor A recebe as inscrições `[1, 2]` em vez de `[1]` |
| Com a correção | Passa. A, B e a coordenação recebem o que lhes cabe; A não altera a nota da disciplina de B (403) |

**Correção.** No backend, não na tela: `escopo.inscricoes_visiveis` (`services/academico/app/services/escopo.py`) e `_detalhe_do_aluno` (`services/academico/app/api/cadastros.py`), usados pelas duas rotas. Gestão continua vendo tudo.

**Verificação.** Acadêmico: 147 testes passam (146 antes mais o novo). `ruff check` e `ruff format --check` limpos. O analítico já filtrava as inscrições por professor (`escopo.filtrar_inscricoes`), então não precisou de mudança.

**Limite.** Esse teste roda com `TestClient` e SQLite, dentro de um serviço. Ele ainda **não** substitui o teste entre serviços da etapa 4.2 e 4.3, que exige o ambiente isolado.

## Checklist (etapa 10)

- [x] Versão e alterações existentes identificadas.
- [ ] Infraestrutura de testes isolada e pronta.
- [ ] Fluxo HTTP → evento → histórico → relatório aprovado.
- [~] Consulta do aluno compartilhado sem vazamento entre professores. **Parcial:** corrigida e coberta por teste de regressão no acadêmico; falta o teste entre serviços com tokens reais.
- [ ] Interrupção e recuperação do worker aprovadas.
- [ ] Entrega confiável/outbox implementada e testada com broker indisponível.
- [ ] Reentrega idempotente e reprocessamento de falhas verificados.
- [ ] Testes de navegador aprovados para funcionalidades existentes.
- [ ] Métricas reais coletadas e dashboards úteis.
- [ ] Alertas acionados e recuperados em simulação.
- [ ] Backup íntegro, criptografado e com estratégia de consistência definida.
- [ ] Cópia externa e recuperação da chave verificadas, ou dependência explicitada.
- [ ] Restauração dos três bancos e das chaves aprovada em ambiente vazio.
- [ ] Aplicação restaurada processa uma nova alteração corretamente.
- [ ] RPO/RTO definidos e resultados medidos.
- [ ] CI implementado; resultado remoto registrado quando executado.
- [ ] Documentação de operação e evidências entregue sem segredos.

## Pendências e decisões

- **Etapas 3 a 9 não foram iniciadas.** São o ambiente isolado de testes, os testes entre serviços, o outbox, o Playwright, o monitoramento, o backup e a restauração, além da integração com o CI.
- **RPO e RTO** precisam de decisão do responsável antes da etapa 7 (a proposta do guia é backup diário, com perda possível de cerca de 24 horas).
- **Cópia externa do backup e a chave de criptografia** dependem de infraestrutura que ainda não foi definida.
