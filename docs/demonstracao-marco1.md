# Roteiro de demonstração — Marco 1

Tempo estimado: 10 minutos. Tudo pelo Swagger do serviço acadêmico, sem escrever código.

## Antes de começar

```bash
cp .env.example .env            # e troque as senhas
docker compose up --build -d
docker compose exec academico python -m app.comandos.seed
```

Deixe abertas três abas:

- http://localhost/api/auth/docs (login)
- http://localhost/api/academico/docs (cadastros e lançamentos)
- http://localhost:15672 (painel do RabbitMQ, usuário e senha do `.env`)

## 1. Arquitetura (1 min)

Mostre `docker compose ps`: gateway, frontend, auth, acadêmico, analítico, worker, Postgres e RabbitMQ. Explique que cada serviço tem o próprio banco (D13) e que o navegador só fala com o gateway.

## 2. Autenticação (1 min)

1. No Swagger do auth, `POST /login` com `coordenacao@simpa.dev` e uma senha errada: **401** com a mensagem genérica "E-mail ou senha inválidos." (RF09 CA01).
2. Repita com a `DEMO_SENHA` do `.env`. Copie o `access_token`.
3. No Swagger do acadêmico, clique em **Authorize** e cole o token.
4. Mostre que, sem o token, qualquer rota responde **401**.

## 3. Cadastro (3 min)

1. `POST /turmas`: `{"codigo": "DEMO-1", "nome": "Turma da banca", "curso": "IA", "periodo_letivo": "2026.2", "turno": "noturno"}`.
2. `POST /disciplinas` com o `turma_id` criado e `professor_id` de um professor (use `GET /disciplinas` para ver os ids que o seed usou).
   - Com `professor_id` do admin: **422 PROFESSOR_INVALIDO**, porque o acadêmico conferiu no auth (D13).
3. `POST /alunos` com o CPF `123.456.789-00`: **422** apontando o campo `cpf` e o dígito verificador. Corrija para `529.982.247-25` e mostre o CPF **mascarado** na resposta (RNF04).
4. Repita a mesma matrícula: **409 MATRICULA_DUPLICADA**.

## 4. Lançamentos (3 min)

1. `POST /inscricoes` com o aluno e a disciplina. Repita: **409 INSCRICAO_DUPLICADA**.
2. `POST /avaliacoes` com nota `5.995`: **422**, só duas casas (D06). Lance N1 `6.00` (peso 4) e N2 `8.00` (peso 6).
3. `POST /frequencias` com 32 aulas e 40 faltas: **422**. Lance 32 aulas e 8 faltas: a resposta traz `frequencia_percentual: "75.00"`, derivado e nunca enviado (D02).
4. No painel do RabbitMQ, mostre as mensagens passando pela exchange `simpa.eventos`; em `docker compose logs analitico-worker`, o worker recebendo cada uma (D14).

## 5. Consulta integrada (1 min)

`GET /alunos/matricula/{matricula}`: cadastro, disciplina, notas e frequência numa única resposta (RF04). Uma matrícula inexistente responde **404** no formato padrão.

## 6. Encerramento (1 min)

1. `PATCH /turmas/{id}` com `{"status": "encerrada"}`.
2. Tente lançar outra nota: **409 DISCIPLINA_ENCERRADA**. Encerrar a turma bloqueou as disciplinas dela (D10).
3. Entre como `coordenacao` e tente reabrir: **403 REABERTURA_RESTRITA**. Como `admin`, funciona.

## Se perguntarem

- **Onde estão os testes?** `services/*/tests`: 59 testes cobrindo validações, unicidade, D10, eventos e login.
- **Os dados são reais?** Não. O seed gera dados 100% sintéticos (RNF04), com casos de fronteira: média 6,00, frequência 75,00%, média 5,99 e uma inscrição sem dados.
- **E o risco?** O evento já chega ao serviço analítico a cada lançamento; o cálculo é o Marco 2.
