# Evidências: testes entre serviços, interface, filas e recuperação

Registro de execução do guia `plano-execucao-qualidade-operacao.md` (10/11/2026). Só entra aqui o que foi executado e conferido. Nada neste arquivo contém credenciais.

## Decisão registrada: RPO e RTO

O responsável aceitou a proposta do guia: **backup diário**, 7 cópias diárias, 4 semanais e teste de restauração semanal. Com isso o **RPO é de até cerca de 24 horas** de alterações. O **RTO ainda não tem valor**: só será declarado depois de medir uma restauração (etapa 8). Se perder um dia de dados for inaceitável, o caminho é recuperação contínua com WAL/PITR, que fica fora desta proposta.

## Estado de partida (etapa 2)

| Item | Resultado |
|---|---|
| Commit de partida | `c06865b` (`fix(academico): consulta integrada do aluno só mostra as inscrições do professor`) |
| Alterações locais antes de começar | Nenhuma |
| Remotos | `origin` = `mariojorgeb/simpa-projeto`; `grupo` = `Victorfiallho/simpa`. O trabalho vai para a branch `claude/dazzling-galileo-q87j8b` do `grupo` |
| `AGENTS.md` | Nenhum no repositório (busca com `find`; o `rg` não está instalado) |
| Ambiente | Contêiner Linux. Docker 29.9.2, Compose v5.6.1, Python 3.13.18, Node 22.23.4, npm 10.9.9 |
| Limitações do ambiente | O daemon do Docker precisa ser iniciado à mão. O Docker Hub limita as requisições (429) e obriga a repetir o `pull`. O proxy bloqueia `pip` e `npm` dentro do `docker build`: as imagens de teste foram construídas com Dockerfiles temporários **fora do repositório**, com `network: host` e o CA do proxy montado só no build. No CI e numa máquina comum o `build` normal do `compose.test.yml` funciona sem isso |

## Etapa 2.5: vazamento na consulta integrada do aluno

`GET /alunos/{id}` e `GET /alunos/matricula/{matricula}` só conferiam se o aluno tinha *alguma* inscrição do professor e devolviam **todas**, com notas e frequências de outro professor (contraria a D03).

- Teste de regressão `test_consulta_integrada_do_aluno_nao_vaza_a_disciplina_de_outro_professor` (`services/academico/tests/test_rbac.py`). **Sem a correção falha** (`[1, 2]` em vez de `[1]`); com ela passa.
- Correção no backend (`escopo.inscricoes_visiveis`, `_detalhe_do_aluno`). Gestão continua vendo tudo.

## Etapa 3: ambiente isolado de testes

| Ação | Resultado |
|---|---|
| Arquivos criados | `compose.test.yml`, `.env.test.example`; `.gitignore` ignora `.env.test`, `.env.restore-test`, `backup.test.toml` e `restore.test.toml` |
| 3.2 `config --quiet` | Válido (`compose.test.yml`; os arquivos de desenvolvimento e produção também continuam válidos) |
| 3.3 build | As 4 imagens `simpa-test/*:local` foram construídas (com o contorno de build descrito acima) |
| 3.4 `up -d --wait` | Os serviços sobem saudáveis |
| 3.5 estado | `ps` mostra todos `(healthy)`; só o gateway publica porta, em `127.0.0.1:18080`; PostgreSQL e RabbitMQ não aparecem no host |
| Prontidão do worker | O `healthcheck` do `analitico-worker` e do `auth-worker` só passa com a fila declarada **e** um consumidor conectado. Conferido: `consumers = 1` em `analitico.recalculo-risco` e `auth.auditoria`, e as ligações à exchange `simpa.eventos` existentes antes do primeiro lançamento |
| Isolamento | Projeto `simpa-test`, rede e volumes próprios, sem `external`, `container_name` nem `network_mode: host`; credenciais sintéticas em `.env.test` |

O ambiente de desenvolvimento (projeto `simpa`) foi apenas **parado** (`docker compose stop`), sem remover contêineres nem volumes, para não competir com o de teste.

## Etapa 4: testes entre serviços

Suíte em `tests/integration/` (HTTP real no gateway, broker real, sem importar os pacotes `app`; `README.md` com a instalação, as dependências ficam em `requirements.txt`).

| Teste | O que prova |
|---|---|
| `test_fluxo_principal` (4.2) | login → cadastros → notas e frequência → histórico → atualização → transição → relatório CSV com e-mail mascarado. Espera por consulta periódica (prazo de 15 s), sem espera fixa |
| `test_permissoes` (4.3), 6 testes | professor A não vê a disciplina de B em nenhum nível do corpo, nas duas rotas do aluno, nas listagens, no histórico do analítico, nem altera ou lança em B; gestão vê as duas; sem token, token inválido e **token expirado** (assinado de verdade pelo auth) recebem 401 |
| `test_worker_interrompido` (4.4) | com o worker parado a mensagem fica na fila e o histórico não muda; ao voltar, atualiza sem novo lançamento; fila de falhas intacta. Religa no `finally` |
| `test_broker_interrompido` (4.6), 4 testes | ver abaixo |
| `test_despachantes_concorrentes` (4.5) | no PostgreSQL real, dois despachantes com a transação aberta ao mesmo tempo pegam eventos **diferentes** (`FOR UPDATE SKIP LOCKED`) e um terceiro não acha nenhum. O SQLite dos testes unitários ignora o `SKIP LOCKED`, então só o teste real prova isso |

**Resultado da execução: 13 testes passam** (12 em cerca de 87 s, mais o de despachantes concorrentes em 20 s). Repetido 3 vezes em sequência sem falha no fluxo principal.

### Etapa 4.5: outbox e entrega confiável (implementada)

Antes: o acadêmico publicava **depois do commit**, sem confirmação e sem registro; com o RabbitMQ fora, o evento se perdia. Agora:

- **Tabela `evento_outbox`** (migração `a4c6e8b0d2f1`): a alteração e o evento são gravados **na mesma transação**. Teste unitário mostra que, se algo falha antes do commit, os dois somem juntos.
- **`academico-despachante`** (container novo, em produção, desenvolvimento e teste): publica com *publisher confirm* e `mandatory`, e só marca `enviado_em` depois da confirmação. Sem fila ligada ou com recusa, o evento continua pendente com espera progressiva (2 s até 5 min). Com o broker fora, nada é marcado nem contado como tentativa. Pega o próximo evento com `FOR UPDATE SKIP LOCKED` (vários despachantes não disputam a linha). Queda entre o envio e a marcação reenvia o mesmo evento.
- **Envelope** com `event_id` (UUID) e `ocorrido_em`.
- **Consumidor idempotente** (tabela `evento_processado`, migração `b6d8f0a2c4e3`): ignora o `event_id` repetido; só anota depois de processar.
- **Falha passageira**: volta pelas filas de espera (5 s, 30 s, 2 min). **Evento inválido ou tentativas esgotadas**: fila de falhas com o motivo no cabeçalho `x-erro`.
- **Reprocessamento**: `python -m app.comandos.reprocessar_falhas` (`--listar`, `--limite`), documentado em `docs/operacao-filas.md`.

Testes de apoio: acadêmico 157 e analítico 286 testes passam; cobertura 87% e 95%.

### Etapa 4.6: testes de recuperação (todos passam)

1. **Broker parado**: o acadêmico segue gravando e respondendo; o evento fica pendente na outbox; ao religar o RabbitMQ o histórico se atualiza **sem novo lançamento**, sem transição duplicada, sem pendências e sem mensagens na fila de falhas.
2. **Entrega repetida**: o mesmo evento publicado mais 2 vezes é ignorado pelo worker (log `evento repetido ignorado`), sem mudar o histórico nem a tabela de eventos processados.
3. **Evento inválido**: vai para a fila de falhas com o motivo, a fila principal não fica reentregando; `--listar` não consome; reprocessar devolve uma vez, sem loop.
4. **Falha passageira**: com o acadêmico fora do ar, a mensagem vai para a fila de espera de 5 s (e **não** direto para a fila de falhas); ao religar, uma nova tentativa atualiza o histórico.

## Defeitos reais que os testes encontraram

| Defeito | Como apareceu | Correção |
|---|---|---|
| Consulta integrada do aluno vazava inscrições de outro professor | Etapa 4.3 (leitura do guia) | Filtro no backend + teste de regressão |
| `--listar` do comando de reprocessamento não terminava: devolvia cada mensagem e a lia de novo (parava só no limite de 1.000) | Teste de integração do evento inválido | Lê um retrato do tamanho da fila e devolve tudo no final; teste unitário novo |
| **As filas de falha dos dois serviços estavam ligadas à mesma exchange `fanout`**: a falha de um serviço aparecia também na fila de falhas do outro (já existia; as 3 mensagens vistas em `auth.auditoria.falhas` eram do analítico) | Conferência do estado das filas depois da suíte | Falha vai direto para a fila do próprio serviço (analítico e auth); teste no auth; o teste de integração confere que a fila do outro não muda |

O terceiro defeito importa para a etapa 6: sem a correção, um alerta de "novas mensagens na fila de falhas" dispararia por erro de outro serviço.

## Checklist (etapa 10)

- [x] Versão e alterações existentes identificadas.
- [x] Infraestrutura de testes isolada e pronta.
- [x] Fluxo HTTP → evento → histórico → relatório aprovado.
- [x] Consulta do aluno compartilhado sem vazamento entre professores (teste unitário e teste entre serviços com tokens reais).
- [x] Interrupção e recuperação do worker aprovadas.
- [x] Entrega confiável/outbox implementada e testada com broker indisponível.
- [x] Reentrega idempotente e reprocessamento de falhas verificados.
- [ ] Testes de navegador aprovados para funcionalidades existentes.
- [ ] Métricas reais coletadas e dashboards úteis.
- [ ] Alertas acionados e recuperados em simulação.
- [ ] Backup íntegro, criptografado e com estratégia de consistência definida.
- [ ] Cópia externa e recuperação da chave verificadas, ou dependência explicitada.
- [ ] Restauração dos três bancos e das chaves aprovada em ambiente vazio.
- [ ] Aplicação restaurada processa uma nova alteração corretamente.
- [~] RPO/RTO definidos e resultados medidos. **RPO definido (backup diário, cerca de 24 h); RTO ainda sem medição.**
- [ ] CI implementado; resultado remoto registrado quando executado.
- [~] Documentação de operação e evidências entregue sem segredos. **Feita para as filas (`docs/operacao-filas.md`); faltam backup e restauração.**

## Pendências e decisões

- **Etapas 5 a 9 não foram iniciadas:** testes de navegador (Playwright), monitoramento das filas, backup, restauração e a integração com o CI.
- **A suíte entre serviços ainda não roda no CI** (etapa 9): hoje ela roda localmente contra o `compose.test.yml`.
- **Topologia já existente:** a exchange `simpa.eventos.falhas` (`fanout`) ficou como legado, porque trocar o argumento da fila principal exigiria recriá-la. Num ambiente com dados, a migração é: esvaziar a fila principal, apagar a fila e subir o worker novo.
- **Cópia externa do backup e a chave de criptografia** dependem de infraestrutura que ainda não foi definida.
