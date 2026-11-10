# Testes de navegador (Playwright)

Chromium real contra o ambiente **isolado** `simpa-test` (`compose.test.yml` na raiz): gateway,
frontend, APIs, workers, PostgreSQL e RabbitMQ de verdade, sem mocks e sem tocar no ambiente de
desenvolvimento. Os dados de cada teste são criados pela API, com nomes únicos, e cada teste usa uma
sessão de navegador nova.

## Preparar

```bash
# 1. Ambiente de teste (na raiz do repositório)
cp .env.test.example .env.test
docker compose --env-file .env.test -p simpa-test -f compose.test.yml up -d --build --wait --wait-timeout 180

# 2. Dependências e navegador
npm --prefix frontend ci
npm --prefix frontend exec -- playwright install chromium
```

No Linux, se faltarem bibliotecas do sistema para o Chromium, use `playwright install --with-deps chromium`.
A versão do Playwright (`1.63.0`) é fixa no `package.json` para casar com o Chromium baixado.

## Rodar

```bash
npm --prefix frontend run test:e2e                  # a suíte toda
npm --prefix frontend run test:e2e -- login.spec.ts # um arquivo
npm --prefix frontend run test:e2e:report           # abre o relatório HTML (mantém um servidor aberto)
```

`SIMPA_BASE_URL` muda o endereço do gateway (padrão `http://127.0.0.1:18080`).

## Cenários

| Arquivo | O que prova |
|---|---|
| `login.spec.ts` | login válido de cada perfil (administração, coordenação, professor, aluno) com o menu certo; login inválido com mensagem genérica; **sessão expirada**: o JWT vencido é assinado de verdade pelo auth, o `expiraEm` do navegador fica no futuro, e é o backend que recusa (401) e leva ao login |
| `escopo-professor.spec.ts` | o professor só vê a própria disciplina de um aluno compartilhado (nos dados aninhados do detalhe) e nenhum aluno só do outro professor |
| `lancamentos.spec.ts` | nota e faltas salvas permanecem depois de recarregar; nota inválida mostra o erro e não altera o que estava gravado |
| `apoio-e-relatorio.spec.ts` | pedido de apoio do aluno aparece para a coordenação; relatório CSV baixado com os registros esperados e e-mail mascarado |
| `usabilidade.spec.ts` | o menu da gestão é alcançável em telas baixas (1280×720 e 1366×768); a situação "Em risco" aparece escrita, não só pela cor (RNF12) |

Seletores por papel e nome acessível; sem esperas fixas nem posições. Cada professor usado nos
testes é criado na hora (`criarProfessor`), então o teste não depende do que outros deixaram no ambiente.

## Cuidados

- **Traces e capturas** (`test-results/`, `playwright-report/`, ambos fora do Git) são guardados só em
  falha. O trace **contém o JWT, o cabeçalho `Authorization` e a senha do ambiente de teste** (conferido
  abrindo um trace). São credenciais sintéticas de um ambiente descartável, mas não publique esses
  artefatos fora do CI privado e use retenção curta.
- Os testes criam usuários no auth de teste por `docker compose exec` (o auth não tem rota para isso).
  Só funciona no projeto `simpa-test`.
- O Playwright transpila TypeScript sem checar tipos (o projeto não tem `@types/node`); o `npm run build`
  do front não inclui esta pasta.
