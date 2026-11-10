# Matriz de rastreabilidade (RNF13)

Liga cada requisito do [SRS v1.0.0](srs-v1.0.0.docx) ao que o implementa e ao que o verifica. Os caminhos são relativos à raiz do repositório. `A`, `AC` e `AN` abreviam `services/auth`, `services/academico` e `services/analitico`.

Estado conferido em 2026-11-09. A coluna **Situação** diz o que está comprovado: ✅ implementado e coberto por teste ou inspeção; 🟡 implementado com lacuna; ⬜ não feito.

## Requisitos funcionais

| Req. | Descrição | Implementação (models, services, rotas) | Verificação | Situação |
|---|---|---|---|---|
| RF01 | Cadastro de alunos | `AC/app/models/aluno.py`, `AC/app/schemas/aluno.py`, `AC/app/services/cadastros.py`, `AC/app/api/cadastros.py` (`/alunos`); front `Cadastros.tsx` (aba Alunos: cadastrar, editar, inativar) | `AC/tests/test_cadastros.py` (matrícula única, CPF inválido e mascarado, exclusão lógica) | ✅ |
| RF02 | Turmas e disciplinas | `AC/app/models/{turma,disciplina}.py`, `AC/app/services/cadastros.py`, `AC/app/api/cadastros.py` (`/turmas`, `/disciplinas`); front `Cadastros.tsx` (abas Turmas, Disciplinas e Inscrições) | `AC/tests/test_cadastros.py`, `AC/tests/test_lancamentos.py` (turma encerrada bloqueia lançamentos, D10) | ✅ |
| RF03 | Avaliações e frequência | `AC/app/models/{avaliacao,frequencia,inscricao,registro_semanal}.py`, `AC/app/services/lancamentos.py`, `AC/app/api/lancamentos.py` (filtro `disciplina_id` nas listagens); eventos em `AC/app/events/`; front `Lancamentos.tsx` | `AC/tests/test_lancamentos.py` (inclui `test_lancamentos_filtram_por_disciplina`), `AC/tests/test_semanas.py`, `AN/tests/test_eventos.py`; telas conferidas de ponta a ponta no navegador em 2026-11-10 | ✅ |
| RF04 | Consulta integrada do aluno | `GET /alunos/{id}` e `GET /alunos/matricula/{matricula}` em `AC/app/api/cadastros.py`; `AN/app/api/rotas.py` (`/indicadores/alunos/{id}`); front `DetalheAluno.tsx` | `AC/tests/test_lancamentos.py` (consulta por matrícula), `AC/tests/test_seguranca_entradas.py` | ✅ |
| RF05 | Indicadores estatísticos | `AN/app/services/estatistica.py`, `AN/app/services/painel.py`, `AN/app/api/rotas.py` (`/painel`, `/indicadores/*`) | `AN/tests/test_estatistica.py` (população × amostra, mediana, correlação), `AN/tests/test_painel.py` | ✅ |
| RF06 | Gráficos | front `VisaoGeral.tsx`, `Analises.tsx`, `Anel.tsx` (Recharts), dados de `/painel` e `/predicao` | Inspeção visual (capturas de 2026-11-09 com 36 alunos); `AN/tests/test_painel.py` cobre os dados | 🟡 sem teste automatizado do front |
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
| RNF03 | Contrato OpenAPI | `*/app/core/openapi.py` (respostas 400, 401, 403, 404, 422, 500 no envelope `ErroPadrao`) | `*/tests/test_contrato.py` (`test_toda_rota_documenta_400_e_500`) | ✅ |
| RNF04 | Privacidade e LGPD | CPF e e-mail mascarados (`AC/app/schemas/base.py`, `AC/app/core/auditoria.py`); só dados sintéticos (seed) | `AC/tests/test_auditoria.py` (CPF no caminho), `AC/tests/test_cadastros.py` (`test_cpf_aparece_mascarado`), `AN/tests/test_painel.py` (e-mail mascarado no relatório); em 2026-11-09 nenhum token, senha ou CPF em `log_requisicao` nem nos logs dos containers | ✅ |
| RNF05 | Documentação técnica | `docs/uml.md`, `docs/der.md`, `docs/srs-v1.0.0.docx`, `docs/decisoes.md` | Inspeção; UML e DER ainda precisam ser revisados contra o código final | 🟡 |
| RNF06 | Organização de pastas | mesma estrutura nos três serviços; `docs/`, `infra/`, `gateway/` | Inspeção da árvore | ✅ |
| RNF07 | Testabilidade | 557 testes (auth 135, acadêmico 145, analítico 277); cobertura 90%, 87% e 95%; mínimo de 80% no CI | CI | ✅ |
| RNF08 | Persistência e integridade | models com FK, `UNIQUE` e `CHECK`; migrações Alembic por serviço; índices compostos | `*/tests/test_indices.py` (migração × models); `AC/tests/test_cadastros.py`; migrações aplicadas em PostgreSQL 17 real em 2026-11-09 (cabeças `f8a0c2e46b17`, `f7b9d1e35a64`, `9c3e5a7b1d86`) | ✅ |
| RNF09 | Interpretabilidade | justificativa objetiva em `AN/app/services/regras.py`; textos em `AN/app/services/interpretacao.py`; front `Achados.tsx`, `Dica.tsx` | `AN/tests/test_regras.py` (justificativa cita nota e frequência), `AN/tests/test_nivel2.py` | ✅ |
| RNF10 | Desempenho (< 300 ms) | índices compostos; paginação | Medido em PostgreSQL com 3.036 alunos e 9.108 inscrições: ver [desempenho.md](desempenho.md) | 🟡 listagens passam; rotas agregadas do analítico não |
| RNF11 | Usabilidade | front React: navegação lateral (rola em telas baixas), retorno de sucesso e erro | `frontend/tests/e2e/`: `lancamentos.spec.ts` (retorno imediato de erro e sucesso), `usabilidade.spec.ts` (menu alcançável em 1280×720 e 1366×768), `login.spec.ts` (mensagens). Falta conferir os campos obrigatórios de forma sistemática | 🟡 |
| RNF12 | Acessibilidade | `Selo.tsx` escreve a situação junto da cor; `aria-*` nos componentes | `usabilidade.spec.ts` confere que "Em risco" aparece em texto; seletores por papel e nome acessível em toda a suíte. Sem auditoria automatizada de contraste | 🟡 |
| RNF13 | Rastreabilidade | este documento | Revisão por amostragem | ✅ |
| RNF14 | Confiabilidade (500 sem stack trace) | handler em `*/app/core/excecoes.py` (`ERRO_INTERNO`, 500) | Os testes só conferem que a rota **documenta** o 500; **não há teste que provoque um erro inesperado** e confira a resposta | 🟡 |
| RNF15 | Segurança de entrada | `*/app/core/entradas.py` (recusa `<`, `>` e controle; `PARAMETRO_REPETIDO`; `LIKE` escapado) | `*/tests/test_seguranca_entradas.py` (SQL injection, XSS, parâmetro repetido); confirmado ao vivo: `limite=1&limite=2` responde 400 | ✅ |
| RNF16 | Logs JSON com Correlation ID | `*/app/core/logs.py`; `X-Request-ID` gerado em `gateway/nginx.conf` | `A/tests/test_api.py` (`test_devolve_o_request_id_recebido_do_gateway`), `*/tests/test_auditoria.py`; o ID do cabeçalho de resposta bate com `log_requisicao.correlation_id` | ✅ |

## Lacunas que a matriz expôs

1. **RNF14**: falta um teste que force uma exceção não tratada e confira corpo padronizado, status 500 e ausência de stack trace.
2. **RNF10**: as rotas agregadas do analítico passam de 3 s com ~9 mil inscrições (ver `desempenho.md`).
3. **RF06**: os gráficos dependem só de inspeção visual. **RNF11 e RNF12** têm testes de navegador parciais; falta auditoria de contraste e conferência sistemática dos campos obrigatórios. As telas de Cadastros ainda não têm teste de navegador (só Lançamentos).
4. **RNF05**: revisar UML e DER contra o código final.
5. **Casos de aceitação**: RF07 CA01–CA03 e RF09 CA01 têm teste nomeado; os demais critérios de aceitação do SRS não foram mapeados um a um.

## Como manter

Ao criar uma rota, model ou teste, acrescente o ID do requisito no docstring ou no nome do teste (como em `test_rf07_ca01_...`) e atualize a linha correspondente aqui.
