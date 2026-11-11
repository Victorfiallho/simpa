# Matriz de rastreabilidade (RNF13)

Liga cada requisito do [SRS v1.0.0](srs-v1.0.0.docx) ao que o implementa e ao que o verifica. Os caminhos são relativos à raiz do repositório. `A`, `AC` e `AN` abreviam `services/auth`, `services/academico` e `services/analitico`.

Estado conferido em 2026-11-11. A coluna **Situação** diz o que está comprovado: ✅ implementado e coberto por teste ou inspeção; 🟡 implementado com lacuna; ⬜ não feito.

## Requisitos funcionais

| Req. | Descrição | Implementação (models, services, rotas) | Verificação | Situação |
|---|---|---|---|---|
| RF01 | Cadastro de alunos | `AC/app/models/aluno.py`, `AC/app/schemas/aluno.py`, `AC/app/services/cadastros.py`, `AC/app/api/cadastros.py` (`/alunos`); front `Cadastros.tsx` (aba Alunos: cadastrar, editar, inativar) | `AC/tests/test_cadastros.py` (matrícula única, CPF inválido e mascarado, exclusão lógica); `frontend/tests/e2e/cadastros.spec.ts` (tela: criar, campo que falhou, editar sem mostrar o CPF, inativar) | ✅ |
| RF02 | Turmas e disciplinas | `AC/app/models/{turma,disciplina}.py`, `AC/app/services/cadastros.py`, `AC/app/api/cadastros.py` (`/turmas`, `/disciplinas`); front `Cadastros.tsx` (abas Turmas, Disciplinas e Inscrições) | `AC/tests/test_cadastros.py`, `AC/tests/test_lancamentos.py` (turma encerrada bloqueia lançamentos, D10); `frontend/tests/e2e/cadastros.spec.ts` (turma, disciplina e inscrição pela tela) | ✅ |
| RF03 | Avaliações e frequência | `AC/app/models/{avaliacao,frequencia,inscricao,registro_semanal}.py`, `AC/app/services/lancamentos.py`, `AC/app/api/lancamentos.py` (filtro `disciplina_id` nas listagens); eventos em `AC/app/events/`; front `Lancamentos.tsx` | `AC/tests/test_lancamentos.py` (inclui `test_lancamentos_filtram_por_disciplina`), `AC/tests/test_semanas.py`, `AN/tests/test_eventos.py`; `frontend/tests/e2e/lancamentos.spec.ts` (nota salva permanece após recarregar; nota inválida não altera o gravado) | ✅ |
| RF04 | Consulta integrada do aluno | `GET /alunos/{id}` e `GET /alunos/matricula/{matricula}` em `AC/app/api/cadastros.py`; `AN/app/api/rotas.py` (`/indicadores/alunos/{id}`); front `DetalheAluno.tsx` | `AC/tests/test_lancamentos.py` (consulta por matrícula), `AC/tests/test_seguranca_entradas.py` | ✅ |
| RF05 | Indicadores estatísticos | `AN/app/services/estatistica.py`, `AN/app/services/painel.py`, `AN/app/api/rotas.py` (`/painel`, `/indicadores/*`) | `AN/tests/test_estatistica.py` (população × amostra, mediana, correlação), `AN/tests/test_painel.py` | ✅ |
| RF06 | Gráficos | front `VisaoGeral.tsx`, `Analises.tsx`, `Anel.tsx` (Recharts), dados de `/painel` e `/predicao` | `frontend/tests/e2e/graficos.spec.ts` (turma com notas conhecidas: título, texto explicativo, eixos, legenda, pontos da dispersão, anéis, estatística, ranking e cores semânticas); `AN/tests/test_painel.py` cobre os dados | ✅ |
| RF07 | Classificação de risco | `AN/app/services/regras.py`, `AN/app/services/risco.py`, `AN/app/models/resultado_risco.py`, worker `AN/app/events/consumidor.py` | `AN/tests/test_regras.py` (`test_rf07_ca01`, `ca02`, `ca03`, fronteiras 6,00 e 75,00%, aluno sem dados) | ✅ |
| RF08 | API REST padronizada | envelope `Resposta` em `*/app/core/respostas.py`; paginação em `*/app/core/paginacao.py` | `*/tests/test_contrato.py`, `*/tests/test_api.py` | ✅ |
| RF09 | Autenticação e acesso | `A/app/core/seguranca.py` (JWT RS256, JWKS), `A/app/services/{usuarios,bloqueio}.py`, `POST /login`; `exigir_roles` e escopo do professor em `AC/app/services/escopo.py`, `AN/app/services/escopo.py` | `A/tests/test_api.py`, `A/tests/test_bloqueio.py` (429 após 5 erros, mensagem genérica), `AC/tests/test_rbac.py`, `AN/tests/test_rbac.py` | ✅ |
| RF10 | Validação de entrada | schemas Pydantic em `*/app/schemas/`; `AC/app/schemas/aluno.py` (CPF com dígitos verificadores); `*/app/core/entradas.py` | `AC/tests/test_cadastros.py`, `*/tests/test_seguranca_entradas.py` | ✅ |
| RF11 | Relatórios e exportação | `AN/app/services/relatorios.py`, `GET /relatorios/inscricoes?formato=csv\|xlsx\|pdf` | `AN/tests/test_painel.py` (`test_relatorio_csv`, `xlsx`, `pdf`, filtro por situação), `AN/tests/test_rbac.py` (professor não exporta) | ✅ |
| RF12 | Auditoria de requisições | `*/app/core/auditoria.py` (evento `log.requisicao`), `A/app/models/log_requisicao.py`, `A/app/services/auditoria.py`, `GET /auditoria`; front `Auditoria.tsx` | `*/tests/test_auditoria.py`, `A/tests/test_auditoria_leitura.py`; conferido em execução real em 2026-11-09 (ver abaixo) | ✅ |

## Requisitos não funcionais

| Req. | Descrição | Implementação | Verificação | Situação |
|---|---|---|---|---|
| RNF01 | Arquitetura em camadas | `app/{api,services,repositories,models,schemas,core}` em cada serviço; D13 | Inspeção da árvore | ✅ |
| RNF02 | Manutenibilidade | `pyproject.toml` (ruff com regras `S`), `*/app/core/excecoes.py`, README | CI (`.github/workflows/ci.yml`: `ruff check`, `ruff format --check`) | ✅ |
| RNF03 | Contrato OpenAPI | `*/app/core/openapi.py` (respostas 400, 401, 403, 404, 422, 500 no envelope `ErroPadrao`) | `*/tests/test_contrato.py` (`test_toda_rota_documenta_400_e_500`); `tests/contrato/test_valores_front_backend.py` (os 17 valores enumerados do front são os do backend; roda no CI) | ✅ |
| RNF04 | Privacidade e LGPD | CPF e e-mail mascarados (`AC/app/schemas/base.py`, `AC/app/core/auditoria.py`); só dados sintéticos (seed) | `AC/tests/test_auditoria.py` (CPF no caminho), `AC/tests/test_cadastros.py` (`test_cpf_aparece_mascarado`), `AN/tests/test_painel.py` (e-mail mascarado no relatório); em 2026-11-09 nenhum token, senha ou CPF em `log_requisicao` nem nos logs dos containers | ✅ |
| RNF05 | Documentação técnica | `docs/uml.md`, `docs/der.md`, `docs/srs-v1.0.0.docx`, `docs/decisoes.md` | Inspeção; UML e DER ainda precisam ser revisados contra o código final | 🟡 |
| RNF06 | Organização de pastas | mesma estrutura nos três serviços; `docs/`, `infra/`, `gateway/` | Inspeção da árvore | ✅ |
| RNF07 | Testabilidade | 656 testes de backend (auth 151, acadêmico 202, analítico 303); cobertura 94%, 88% e 95%; mínimo de 80% no CI; testes entre serviços e de navegador no `integracao.yml` | CI | ✅ |
| RNF08 | Persistência e integridade | models com FK, `UNIQUE` e `CHECK`; migrações Alembic por serviço; índices compostos | `*/tests/test_indices.py` (migração × models); `AC/tests/test_cadastros.py`; migrações aplicadas em PostgreSQL 17 real em 2026-11-09 (cabeças `f8a0c2e46b17`, `f7b9d1e35a64`, `9c3e5a7b1d86`) | ✅ |
| RNF09 | Interpretabilidade | justificativa objetiva em `AN/app/services/regras.py`; textos em `AN/app/services/interpretacao.py`; front `Achados.tsx`, `Dica.tsx` | `AN/tests/test_regras.py` (justificativa cita nota e frequência), `AN/tests/test_nivel2.py` | ✅ |
| RNF10 | Desempenho (< 300 ms) | índices compostos; paginação | Medido em PostgreSQL com 3.036 alunos e 9.108 inscrições: ver [desempenho.md](desempenho.md) | 🟡 listagens passam; rotas agregadas do analítico não |
| RNF11 | Usabilidade | front React: navegação lateral (rola em telas baixas), retorno de sucesso e erro; campos obrigatórios com asterisco e legenda (`componentes/Obrigatorio.tsx`) | `frontend/tests/e2e/`: `lancamentos.spec.ts` (retorno imediato de erro e sucesso), `usabilidade.spec.ts` (menu alcançável em 1280×720 e 1366×768), `login.spec.ts` (mensagens), `campos-obrigatorios.spec.ts` (em cada formulário, os campos com asterisco são exatamente os `required`; envio vazio não cadastra) | ✅ |
| RNF12 | Acessibilidade | `Selo.tsx` escreve a situação junto da cor; `aria-*` nos componentes; `--texto-3` com contraste de 4,5:1 | `usabilidade.spec.ts` confere que "Em risco" aparece em texto; `contraste.spec.ts` roda o axe-core (regra `color-contrast`, WCAG 2.1 AA) no login e nas telas da coordenação, do admin e do aluno; seletores por papel e nome acessível em toda a suíte | ✅ |
| RNF13 | Rastreabilidade | este documento | Revisão por amostragem | ✅ |
| RNF14 | Confiabilidade (500 sem stack trace) | handler em `*/app/core/excecoes.py` (`ERRO_INTERNO`, 500, com o `X-Request-ID`) | `*/tests/test_erro_inesperado.py`: uma exceção não tratada responde 500 padronizado, sem traceback nem mensagem interna; o detalhe fica no log, a resposta traz o `X-Request-ID` e a requisição entra na auditoria | ✅ |
| RNF15 | Segurança de entrada | `*/app/core/entradas.py` (recusa `<`, `>` e controle; `PARAMETRO_REPETIDO`; `LIKE` escapado) | `*/tests/test_seguranca_entradas.py` (SQL injection, XSS, parâmetro repetido); confirmado ao vivo: `limite=1&limite=2` responde 400 | ✅ |
| RNF16 | Logs JSON com Correlation ID | `*/app/core/logs.py`; `X-Request-ID` gerado em `gateway/nginx.conf` | `A/tests/test_api.py` (`test_devolve_o_request_id_recebido_do_gateway`), `*/tests/test_auditoria.py`; o ID do cabeçalho de resposta bate com `log_requisicao.correlation_id` | ✅ |

## Lacunas que a matriz expôs

1. **RNF10**: as rotas agregadas do analítico passam de 3 s com ~9 mil inscrições (ver `desempenho.md`).
2. **RNF05**: revisar UML e DER contra o código final.

Fechadas em 2026-11-11: RNF14 (teste do erro inesperado, que encontrou a resposta 500 sem o `X-Request-ID`), RF06 (testes de navegador dos gráficos), RNF11 (campos obrigatórios indicados e conferidos), RNF12 (auditoria de contraste, que encontrou o `--texto-3` abaixo de 4,5:1) e o mapeamento dos critérios de aceitação, abaixo.

## Critérios de aceitação (SRS, seção 6)

Os 36 critérios, cada um ligado ao teste que o comprova. Os testes criados para um critério levam o ID no nome (`test_rf01_ca03_...`); os sem caminho ficam no `tests/test_criterios_aceitacao.py` do serviço da linha. `E2E` abrevia `frontend/tests/e2e`.

| Critério | O que exige | Teste |
|---|---|---|
| RF01 CA01 | Aluno válido é cadastrado e fica disponível para consulta | `AC/tests/test_lancamentos.py::test_consulta_integrada_do_aluno`; `E2E/cadastros.spec.ts` |
| RF01 CA02 | Matrícula repetida é rejeitada no cadastro e na atualização | `AC/tests/test_cadastros.py::test_matricula_unica`; `test_rf01_ca02_matricula_nao_pode_ser_trocada_na_atualizacao` |
| RF01 CA03 | CPF inválido ou já existente é rejeitado | `AC/tests/test_cadastros.py::test_cpf_invalido`; `test_rf01_ca03_cpf_ja_cadastrado_e_rejeitado`, `test_rf01_ca03_cpf_de_outro_aluno_e_rejeitado_na_atualizacao` |
| RF01 CA04 | Atualizar dados e mudar o status para cada valor previsto | `test_rf01_ca04_atualiza_os_dados_do_aluno`, `test_rf01_ca04_status_do_aluno_aceita_cada_valor_previsto`, `test_rf01_ca04_status_fora_da_lista_e_rejeitado` |
| RF02 CA01 | Turma ou disciplina válida é cadastrada e consultável | fixtures `turma` e `disciplina` de `AC/tests/conftest.py`; `E2E/cadastros.spec.ts` |
| RF02 CA02 | Código repetido é rejeitado | `AC/tests/test_cadastros.py::test_codigo_de_turma_unico`; `test_rf02_ca02_codigo_de_disciplina_ja_existente_e_rejeitado` |
| RF02 CA03 | Exclusão física de turma com vínculos é impedida | `AC/tests/test_lancamentos.py::test_banco_bloqueia_exclusao_fisica_com_historico` |
| RF02 CA04 | Atualizar e inativar o cadastro | `test_rf02_ca04_atualiza_e_inativa_turma_e_disciplina` |
| RF03 CA01 | Nota fora de 0,00 a 10,00 é rejeitada | `AC/tests/test_lancamentos.py::test_nota_fora_de_0_a_10_e_recusada` |
| RF03 CA02 | Frequência fora de 0 a 100% e peso menor ou igual a zero são rejeitados | `test_faltas_nao_passam_das_aulas`, `test_percentual_nao_e_aceito_na_entrada` (o percentual é derivado de faltas e aulas, D02); `test_rf03_ca02_peso_menor_ou_igual_a_zero_e_rejeitado` |
| RF03 CA03 | Alteração válida recalcula indicadores e risco | `AC/tests/test_lancamentos.py::test_cada_alteracao_publica_um_evento`; `AN/tests/test_eventos.py::test_evento_grava_a_classificacao_da_inscricao`; `tests/integration/test_fluxo_principal.py` |
| RF04 CA01 | Consulta por id ou matrícula traz a visão consolidada | `AC/tests/test_lancamentos.py::test_consulta_integrada_do_aluno` |
| RF04 CA02 | Aluno inexistente responde 404 | `AC/tests/test_cadastros.py::test_aluno_inexistente_responde_404` |
| RF05 CA01 | Indicadores em cada nível de agregação | `AN/tests/test_criterios_aceitacao.py::test_rf05_ca01_indicadores_em_cada_nivel_de_agregacao` (aluno, disciplina, turma e período) |
| RF05 CA02 | Média ponderada pelos pesos, com duas casas | `test_rf05_ca02_media_ponderada_com_duas_casas`; `AN/tests/test_regras.py::test_media_ponderada_pelos_pesos` |
| RF05 CA03 | Variância amostral na análise parcial e populacional no universo completo | `AN/tests/test_painel.py::test_janela_parcial_usa_variancia_amostral`, `test_indicadores_da_turma`; `AN/tests/test_estatistica.py::test_resumo_amostral_divide_por_n_menos_1` |
| RF06 CA01 | Os gráficos refletem o banco | `E2E/graficos.spec.ts` (valores exatos de uma turma criada pelo teste) |
| RF06 CA02 | Título, eixos e legenda em cada gráfico | `E2E/graficos.spec.ts` |
| RF06 CA03 | Cores semânticas de status | `E2E/graficos.spec.ts` (cor dos pontos da dispersão); `E2E/usabilidade.spec.ts` (situação também em texto) |
| RF07 CA01 | Média abaixo de 6,0 com frequência de 75% ou mais: Em Risco, com `media_baixa` | `AN/tests/test_regras.py::test_rf07_ca01_media_baixa_e_risco` |
| RF07 CA02 | Média de 6,0 ou mais com frequência abaixo de 75%: Em Risco, com `frequencia_baixa` | `test_rf07_ca02_frequencia_baixa_e_risco` |
| RF07 CA03 | Média 6,0 e frequência 75,0%: Sem Risco | `test_rf07_ca03_criterios_atendidos_e_sem_risco`, `test_fronteira_exata_e_sem_risco_com_atencao` |
| RF07 CA04 | Critério violado e justificativa compreensível | `test_os_dois_criterios_aparecem_na_justificativa`; `AN/tests/test_painel.py::test_painel_consolida_alunos_e_situacoes` |
| RF08 CA01 | Respostas JSON no contrato padronizado | `*/tests/test_contrato.py` |
| RF08 CA02 | Toda listagem aceita paginação, ordenação e filtro | `AC/tests/test_criterios_aceitacao.py::test_rf08_ca02_*` (lê as listagens do OpenAPI); `A/tests/test_auditoria_leitura.py` (`/auditoria`) |
| RF09 CA01 | Credenciais válidas emitem JWT com expiração | `A/tests/test_usuarios.py::test_rf09_ca01_token_emitido_tem_prazo_de_expiracao` |
| RF09 CA02 | Login inválido: 401 genérico | `A/tests/test_usuarios.py::test_login_invalido_tem_mensagem_generica`; `A/tests/test_bloqueio.py::test_mensagem_do_401_continua_generica`; `E2E/login.spec.ts` |
| RF09 CA03 | Rota protegida sem token válido: 401 | `AC/tests/test_api.py::test_token_invalido_responde_401`; `AN/tests/test_painel.py::test_sem_token_responde_401`; `A/tests/test_auditoria_leitura.py::test_sem_token_e_401` |
| RF10 CA01 | Payload inválido não persiste nada | `AC/tests/test_lancamentos.py::test_erro_de_validacao_nao_publica_evento`; `E2E/cadastros.spec.ts` (dados inválidos, nada é criado) |
| RF10 CA02 | Erro informa campo, regra e código interno | `AC/tests/test_cadastros.py::test_validacao_informa_campo_regra_e_codigo`; `*/tests/test_contrato.py::test_erro_422_lista_os_campos_invalidos` |
| RF11 CA01 | O relatório respeita os filtros | `AN/tests/test_painel.py::test_relatorio_filtra_por_situacao`; `test_rf11_ca01_relatorio_repassa_os_filtros_e_os_registra` |
| RF11 CA02 | Download em CSV, XLSX e PDF | `AN/tests/test_painel.py::test_relatorio_csv_tem_cabecalho_e_email_mascarado`, `test_relatorio_xlsx`, `test_relatorio_pdf`; `E2E/apoio-e-relatorio.spec.ts` |
| RF11 CA03 | Data, hora e usuário no arquivo | `test_relatorio_csv_tem_cabecalho_e_email_mascarado`; `test_rf11_ca03_xlsx_identifica_data_hora_e_usuario`, `test_rf11_ca03_pdf_identifica_data_hora_e_usuario` |
| RF12 CA01 | Cada requisição gera um registro com os campos definidos | `AC/tests/test_auditoria.py::test_registra_a_requisicao`, `test_so_envia_os_campos_previstos`; `A/tests/test_auditoria.py::test_grava_o_registro`; `*/tests/test_erro_inesperado.py` (também no 500) |
| RF12 CA02 | Requisição autenticada leva o `usuario_id` | `AC/tests/test_auditoria.py::test_usuario_do_token_vai_para_o_registro` |
| RF12 CA03 | Nenhum registro expõe senha, token ou CPF completo | `AC/tests/test_auditoria.py::test_cpf_no_caminho_e_mascarado`; `A/tests/test_auditoria.py::test_login_e_registrado_sem_senha_nem_corpo` |

## Como manter

Ao criar uma rota, model ou teste, acrescente o ID do requisito no docstring ou no nome do teste (como em `test_rf07_ca01_...`) e atualize a linha correspondente aqui.
