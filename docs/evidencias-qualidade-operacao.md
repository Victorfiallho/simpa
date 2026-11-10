# Evidências: testes entre serviços, interface, filas e recuperação

Registro de execução do guia `plano-execucao-qualidade-operacao.md` (10/11/2026). Só entra aqui o que foi executado e conferido. Nada neste arquivo contém credenciais.

## Decisão registrada: RPO e RTO

O responsável aceitou a proposta do guia: **backup diário**, 7 cópias diárias, 4 semanais e teste de restauração semanal. Com isso o **RPO é de até cerca de 24 horas** de alterações. O **RTO** foi medido uma vez (etapa 8): 30 s numa base de teste pequena; não é promessa para produção. Se perder um dia de dados for inaceitável, o caminho é recuperação contínua com WAL/PITR, que fica fora desta proposta.

## Estado de partida (etapa 2)

| Item | Resultado |
|---|---|
| Commit de partida | `c06865b` (`fix(academico): consulta integrada do aluno só mostra as inscrições do professor`) |
| Alterações locais antes de começar | Nenhuma |
| Remotos | `origin` = `mariojorgeb/simpa-projeto`; `grupo` = `Victorfiallho/simpa`. O trabalho vai para a branch de trabalho do `grupo` |
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

## Etapa 5: testes de navegador (Playwright)

Playwright `1.63.0` (versão fixa, casa com o Chromium do ambiente), `frontend/playwright.config.ts` e `frontend/tests/e2e/` (README com a instalação e os cuidados). Chromium real contra o ambiente isolado da etapa 3, sem mocks.

| Cenário do guia | Teste | Situação |
|---|---|---|
| 1. Login válido de cada perfil | `login.spec.ts` (administração, coordenação, professor, aluno) | passa |
| 2. Login inválido | `login.spec.ts` | passa |
| 3. Professor só no seu escopo, inclusive dados aninhados | `escopo-professor.spec.ts` | passa |
| 4. Nota salva permanece após recarregar | `lancamentos.spec.ts` | passa |
| 5. Entrada inválida mostra erro e não altera dados | `lancamentos.spec.ts` e `cadastros.spec.ts` | passa |
| 6. Sessão realmente expirada | `login.spec.ts`: JWT vencido assinado pelo auth, `expiraEm` do navegador no futuro; o backend responde 401 e a tela volta ao login | passa |
| 7. Pedido de apoio do aluno aparece para a coordenação | `apoio-e-relatorio.spec.ts` | passa |
| 8. Relatório baixado com os registros esperados | `apoio-e-relatorio.spec.ts` (CSV, e-mail mascarado) | passa |
| Telas de Cadastros (RF01, RF02) | `cadastros.spec.ts`: criar turma, disciplina, aluno e inscrição pela matrícula; dados inválidos e matrícula repetida; editar sem mostrar o CPF e inativar mantendo o histórico; aluno em turma fora das 100 mais recentes; professor sem acesso | passa |
| Usabilidade e acessibilidade | `usabilidade.spec.ts`: menu alcançável em telas baixas; "Em risco" em texto (RNF12) | passa |

**Resultado: 19 testes passam.** Estabilidade medida, não presumida: a suíte inteira repetida 3 vezes seguidas (57 execuções, 0 falha) e o teste de lançamento repetido 15 vezes (30 execuções, 0 falha). A primeira medição achou instabilidades reais (abaixo), e foi a repetição que as mostrou: uma execução isolada passava.

**Controle negativo.** O teste do aluno em turma antiga foi conferido desligando a correção de propósito: ele falhou como previsto (`Expected "615"`, `Received ""`) e voltou a passar com o código bom.

**Credenciais nos traces.** O trace de falha traz o que o navegador e o teste enviaram. Medido abrindo traces de verdade:

| Teste | Senha do ambiente de teste no trace | Token (JWT) |
|---|---|---|
| Qualquer teste que não é de login | **não aparece**: o login e a preparação de dados usam o `fetch` do Node, que o Playwright não grava, e a sessão é entregue ao navegador sem digitar a senha | aparece 1 (o da sessão do navegador) |
| `login.spec.ts` (válido) | aparece, porque o teste digita a senha na tela | aparece |

São credenciais sintéticas de um ambiente descartável, e o token vale 60 minutos. Mesmo assim os artefatos de falha não devem sair do CI privado e precisam de retenção curta.

**Contrato dos valores permitidos entre front e backend.** `tests/contrato/test_valores_front_backend.py` (17 enumerados: motivos e estados de apoio, tipos e níveis de alerta, estado do atendimento, tipo de acompanhamento, base do cenário, situação, janela, formato, perfis, status de turma, disciplina, aluno e inscrição, turno e tipo de avaliação). Não precisa do ambiente, e **já roda no CI** (job de backend). Conferido: ao tirar `evadido` do front ele falha e aponta `só no backend: ['evadido']`.

**Limitação do ambiente desta execução.** O build da imagem do frontend dentro do Docker falhou aqui (`npm ci` com "Exit handler never called!", rede do proxy), inclusive com o lockfile original, então o problema é do ambiente e não da mudança. Para testar, o `dist` foi gerado fora do contêiner (`npm run build`) e empacotado no nginx por um Dockerfile temporário fora do repositório. O artefato é o mesmo.

**Lockfile.** O `npm install` local (10.9.9) reescreveria o lockfile e apagaria os campos `libc` de dependências opcionais que já existiam. Mantive o lockfile original e acrescentei **só** as 3 entradas do Playwright (46 inserções, 0 remoções); o `npm ci` passa.

## Etapa 6: monitoramento das filas

Camada separada, `compose.monitoramento.yml` + `infra/monitoramento/` (Prometheus `v2.55.1`, Alertmanager `v0.27.0`, Grafana `11.3.1`, versões fixas; retenção de 15 dias ou 2 GB; painéis só em `127.0.0.1`; métricas só na rede interna). Documentação de operação, com o que fazer em cada alerta, em `docs/operacao-filas.md`.

| Item do guia | O que foi feito e como foi provado |
|---|---|
| 6.1 Métricas | O plugin `rabbitmq_prometheus` já vem ativo no RabbitMQ 4.4.0. **Os nomes e rótulos foram listados no RabbitMQ real antes de escrever qualquer consulta** (por fila: `rabbitmq_detailed_queue_messages_ready`, `…_unacked`, `…_consumers`; globais: `rabbitmq_global_messages_*_total`). Os 4 alvos de coleta ficam `up` |
| 6.2 Instrumentação do caminho do evento | Despachante e worker expõem `/metrics` (`prometheus-client==0.21.1`): mensagens prontas, não confirmadas e consumidores (RabbitMQ); novas mensagens na fila de falhas; taxas de publicação, entrega e confirmação; **idade do evento mais antigo na outbox**; **latência da alteração ao fim do processamento** (usa o `ocorrido_em` do envelope, não o tamanho da fila); eventos por resultado; falhas e reconexões. Nenhum rótulo com nome, e-mail, token ou id. Testes unitários para os contadores e medidores (acadêmico 167, analítico 290 testes) |
| 6.3 Alertas | 12 regras com os limites iniciais do guia (consumidor ausente 1 min, fila de falhas, evento pendente 2 min, crescimento 5 min, coleta ausente), mais mensagem sem destino, latência, reconexões e despachante parado. **Série ausente é alerta** (`FilaEsperadaAusente`, `AlvoDeColetaSumiu`), e o painel mostra "sem dado" em vermelho. Menos ruído: `for:` em todas e 2 inibições no Alertmanager |
| 6.3 Prova das regras | `promtool test rules`: **15 casos**, cada alerta nos dois sentidos (dispara e fica quieto). Controle negativo: com 2 regras estragadas de propósito, os testes falharam |
| 6.4 Simulação | `tests/integration/test_monitoramento.py`, 3 cenários reais: (1) worker parado → `FilaSemConsumidor` e `ColetaDeMetricasAusente` disparam depois de 1 minuto, a notificação chega ao receptor e a normalização também; (2) evento inválido → `FilaDeFalhasRecebeuMensagens` dispara e **a fila de falhas do auth não acende**; (3) broker parado → `EventoPendenteNaOutbox`, coleta do RabbitMQ e **inibição** de `FilaEsperadaAusente` (consequência, não notificada), e o evento que esperou na outbox **chega ao histórico** depois da recuperação. **3 passam** (6m31s) |
| Destinos | O Alertmanager entrega só a um **receptor local de teste**. Nada foi enviado a pessoas nem a canais externos |
| Dashboard | `SIMPA — Filas de eventos` (16 painéis), provisionado; fonte de dados saudável; acesso anônimo negado (401); sem painéis com erro; conferido por captura de tela com dados reais |
| CI | Novo job `monitoramento`: `promtool check config` e `test rules`, `amtool check-config`, JSON do dashboard e `config` do Compose. **Ainda não rodou no CI remoto** |

**Regressão completa:** depois das mudanças nos laços de reconexão, a suíte entre serviços inteira passou, **16 testes** (13 + 3 do monitoramento, 8m22s). Unitários: auth 137 (94%), acadêmico 167 (88%), analítico 290 (95%).

## Etapa 8: restauração verificada (etapa 7 só em versão mínima)

Como a etapa 8 precisa de um pacote para restaurar, foi feito **só o produtor mínimo** de backup; o resto da etapa 7 ficou de fora (ver pendências).

**O que existe** (`scripts/backup/`):
- `cripto.py`: AES-256-GCM em blocos de 1 MiB (STREAM). O bloco final é marcado nos dados autenticados, então truncar, trocar blocos de ordem ou acrescentar lixo é detectado. A chave vem de arquivo `0600` (nunca da linha de comando) e fica fora do pacote.
- `criar_backup.py`: **janela controlada** para a consistência entre os três bancos. As APIs param, a outbox e as filas esvaziam, os workers param, o dump é feito e tudo volta no `finally`. Escreve `.parcial` e renomeia; nunca sobrescreve. O pacote tem os três bancos (`pg_dump -Fc`), os papéis do PostgreSQL (guardados, não aplicados), o par de chaves de assinatura do auth e um manifesto (commit, versão do PostgreSQL, migração de cada serviço, hash de cada arquivo; sem senhas).
- `restaurar_backup.py`: só aceita destino `simpa-test*`/`simpa-restore-test*` e exige repetir o nome em `--confirmo-destino`; recusa chave errada, pacote corrompido ou truncado, hash diferente do manifesto, tar com caminho perigoso, banco de destino com tabelas e migração diferente da esperada pela imagem. Cada banco entra com `pg_restore --single-transaction --exit-on-error`. As chaves vão para o volume do destino antes de o auth subir.
- `provar_restauracao.py` + `compose.restore-test.yml`: ambiente próprio (`simpa-restore-test`, porta 18081, volumes próprios, **sem `USUARIOS_DEMO`**, então os usuários só existem se vieram do backup).

**Resultado da prova ao vivo (origem parada durante a verificação): APROVADO**

| Conferência | Resultado |
|---|---|
| JWKS do restaurado idêntico ao da origem; token emitido na origem aceito | ✅ |
| Login de administrador e professor (usuários vieram do backup) | ✅ |
| Relatório de inscrições idêntico (461 linhas), notas e histórico de risco idênticos | ✅ |
| Dado criado **depois** do backup não existe no restaurado (mostra o ponto de recuperação) | ✅ |
| Mudança nova no restaurado é processada pelo worker e gera histórico | ✅ |

**Medidas (ambiente de teste, base pequena, ~560 KB cifrados):** backup 47 s no total, com 15 s sem escrita; restauração dos três bancos 0,2 s cada, chaves 0,4 s; **do início da restauração até o login funcionando: 30 s**. Valores de uma base pequena, em uma máquina: servem de piso, não de promessa para produção. **RTO medido só vale para este tamanho de dados**; com volume real é preciso repetir.

**Recusas conferidas:** destino de desenvolvimento (`simpa`), destino não vazio (nada escrito), byte alterado, arquivo truncado, chave errada, versão de migração diferente. Testes sem Docker em `tests/backup/` (22 testes); as recusas com Docker foram executadas à mão e constam acima.

## Defeitos reais que os testes encontraram

| Defeito | Como apareceu | Correção |
|---|---|---|
| **Com o contêiner do RabbitMQ parado, o despachante e os dois workers morriam** em vez de reconectar. O nome do broker some da rede do Docker e o pika levanta `socket.gaierror` (um `OSError`, não um `AMQPError`), que os laços de reconexão não capturavam. Só voltavam pelo `restart` do Docker. Já existia antes do monitoramento | Etapa 6, simulação do broker parado: as métricas do despachante sumiram | `ERROS_DO_BROKER = (AMQPError, OSError)` nos 3 laços; 3 testes (um por serviço) que **falham sem a correção** |
| **Com o broker fora, as métricas da outbox congelavam**, justamente quando o atraso mais importa: elas só eram atualizadas depois de conectar ao broker, e o alerta de evento pendente ficava cego | Etapa 6, mesma simulação: `EventoPendenteNaOutbox` não disparou em 4 minutos | As métricas da outbox são atualizadas numa thread própria, independente da conexão; o teste de simulação passou a provar o alerta |
| Painel "Fila de falhas" ficava **verde com "sem dado"**: uma fila inexistente parecia saudável | Captura do dashboard durante a simulação | Série ausente vira "sem dado" em vermelho em todos os painéis de estado |
| **Nenhum aluno conseguia enviar um pedido de apoio pela tela**: os 4 motivos do front ("Dificuldade no conteúdo"…) não existem na lista do backend ("Dificuldade com o conteúdo"…), e toda tentativa dava "Selecione um dos motivos da lista" | Etapa 5, cenário 7 (a conferência de contrato que eu tinha feito antes olhou os campos, não os valores permitidos) | Front com os motivos do backend e teste `test_motivos_do_front_sao_os_do_backend` (analítico), que lê o `MeuApoio.tsx` e falha se os dois divergirem |
| **O menu lateral da gestão não rolava**: com 11 itens (1.125 px), em 1366×768 os itens "Pendências", "Auditoria" e "Meu perfil" ficavam fora da tela e inalcançáveis. Já existia; o item "Cadastros" piorou | Etapa 5: o teste do apoio falhava em 3 de 4 execuções com "element is outside of the viewport" | `overflow-y: auto` no menu (o perfil continua fixo embaixo) e `usabilidade.spec.ts` em 1280×720 e 1366×768 |
| As telas de Lançamentos e de Inscrições carregavam só as primeiras 100 disciplinas, **sem avisar** | Etapa 5: o seletor não mostrava a disciplina nova | Aviso "Mostrando as primeiras N de M disciplinas ativas" |
| **O nome da turma saía como "Turma 199"** quando a turma estava fora das 100 primeiras da lista (Lançamentos e Cadastros). Era também a causa de uma instabilidade nos testes (5 falhas em 30 execuções) | Repetir o teste de lançamento 15 vezes | O nome que falta é buscado direto por `GET /turmas/{id}` (`useNomesDeTurma`); teste repetido 30 vezes sem falha |
| **O seletor de turma dos formulários de Cadastros ficava sem a turma nova** (lista alfabética cortada em 100): não dava para cadastrar aluno numa turma fora da lista. Em edição, o seletor ficava vazio e o formulário não podia ser enviado | Repetir a suíte 3 vezes: o teste de dados inválidos falhou 2 de 3 | A lista traz as turmas mais recentes; o formulário de edição inclui sempre a turma atual do aluno; aviso de corte; teste com 100 turmas mais novas e controle negativo |
| **O front não conhecia o status de aluno `evadido`**, que o backend aceita: apareceria com o texto cru e o formulário de edição mostraria a situação errada | Auditoria de todos os valores enumerados (a conferência anterior só olhava os campos) | Front com `evadido`; `tests/contrato` confere os 17 enumerados e roda no CI |
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
- [x] Testes de navegador aprovados para funcionalidades existentes (19 testes, incluindo as telas de Cadastros).
- [x] Métricas reais coletadas e dashboards úteis.
- [x] Alertas acionados e recuperados em simulação.
- [~] Backup íntegro, criptografado e com estratégia de consistência definida. **Feito na versão mínima (janela controlada, AES-256-GCM, manifesto com hashes); faltam retenção, agendamento e simulação de falha do backup.**
- [ ] Cópia externa e recuperação da chave verificadas, ou dependência explicitada.
- [x] Restauração dos três bancos e das chaves aprovada em ambiente vazio.
- [x] Aplicação restaurada processa uma nova alteração corretamente.
- [~] RPO/RTO definidos e resultados medidos. **RPO definido (backup diário, cerca de 24 h); RTO medido em 30 s numa base pequena, a repetir com volume real.**
- [x] CI implementado; resultado remoto registrado. **`integracao.yml` aprovado no PR #18 do grupo (execução 42917157060, commit `f0a8439`, cerca de 17 min): testes entre serviços, de navegador e prova de restauração.** A execução equivalente no `simpa-projeto` ainda estava em andamento quando isto foi escrito.
- [~] Documentação de operação e evidências entregue sem segredos. **Feita para as filas (`docs/operacao-filas.md`); faltam backup e restauração.**

## Pendências e decisões

- **Etapa 7 pulada a pedido, exceto o produtor mínimo; etapa 9 não iniciada.** Da etapa 7 faltam: política de retenção (7 diárias, 4 semanais), agendamento/automação, cópia externa, conferência da custódia da chave e simulação de falha do backup (disco cheio, container parado no meio). Sem agendamento, hoje o backup só existe se alguém o rodar. A etapa 9 é a integração das suítes com o CI. O monitoramento (etapa 6) está feito, com o limite abaixo.
- **Etapa 9 (CI):** `ci.yml` continua rápido e agora também roda `tests/contrato` e `tests/backup` (sem Docker). O novo `integracao.yml` constrói e sobe o ambiente completo (com monitoramento) e roda, em ordem: testes entre serviços, testes de navegador e a prova de restauração (chave descartável por execução; relatório `restauracao.json` publicado como artefato). Dispara em pull request, push na `main`, **toda segunda-feira** (restauração semanal do plano) e sob demanda. O relatório do Playwright só é publicado se algo falhar, porque os traces podem conter o token do ambiente de teste. A primeira execução real passou em cerca de 17 min, dentro do prazo de 45 min.
- **Alertas com limites iniciais:** os limites (1 min, 2 min, 5 min, 60 s) são os do guia e precisam ser ajustados depois de observar carga real. O destino dos alertas é um receptor local de teste: para e-mail ou chat é preciso decidir o canal e ter autorização.
- **Monitoramento só no ambiente de teste:** foi validado com `compose.test.yml`. A camada também funciona sobre o `docker-compose.yml` de desenvolvimento (a configuração é válida), mas esse uso não foi exercitado de ponta a ponta.
- **Filtro global de turmas** (cabeçalho do painel, `App.tsx`): também carrega só as 100 primeiras turmas em ordem alfabética, sem aviso. Fica fora desta correção e vale tratar junto com uma busca por turma.
- **Topologia já existente:** a exchange `simpa.eventos.falhas` (`fanout`) ficou como legado, porque trocar o argumento da fila principal exigiria recriá-la. Num ambiente com dados, a migração é: esvaziar a fila principal, apagar a fila e subir o worker novo.
- **Cópia externa do backup e a chave de criptografia** dependem de infraestrutura que ainda não foi definida.
