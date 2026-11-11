# Desempenho: índices e como medir (RNF08)

## O que já está feito

Os índices foram revisados contra as consultas reais do código. Dois testes por serviço guardam o resultado
(`tests/test_indices.py`):

- as migrações, renderizadas para PostgreSQL sem banco (`alembic upgrade head --sql`), geram
  exatamente os índices declarados nos models;
- as consultas quentes usam o índice e não precisam ordenar à parte (plano do SQLite, que é só uma
  aproximação do PostgreSQL).

| Serviço | Tabela | Índice | Consulta que atende |
|---|---|---|---|
| analítico | `resultado_risco` | `(inscricao_id, id)` | última linha da inscrição e histórico (`WHERE inscricao_id ORDER BY id DESC`); roda a cada evento do acadêmico |
| analítico | `acompanhamento` | `(aluno_id, data, id)` | acompanhamentos do aluno, do mais recente |
| analítico | `solicitacao_apoio` | `(aluno_id, id)`, `(estado, id)` | pedidos do aluno e fila da coordenação por estado |
| analítico | `historico_apoio` | `(solicitacao_id, id)` | histórico de um pedido, em ordem |
| analítico | `atendimento_alerta` | (nenhum extra) | a `UNIQUE(aluno_id, tipo, disciplina_id)` já atende a busca por aluno; o índice só de `aluno_id` foi removido |
| auth | `log_requisicao` | `(usuario_id, timestamp)`, `(status_http, timestamp)`, `timestamp` | trilha de auditoria do mais recente; é a tabela que mais cresce |

O acadêmico já estava coberto: toda FK e os filtros de listagem (`turma_id`, `periodo_letivo`, `professor_id`)
têm índice, e as `UNIQUE` compostas atendem os lançamentos.

## Medição de 2026-11-09 (PostgreSQL 17 real, Docker)

**Carga:** 3.036 alunos, 9.108 inscrições, 18.214 notas e frequências, 500 mil linhas em `log_requisicao`, 9.108 resultados de risco. Dados sintéticos gerados por SQL (`generate_series`) direto nos bancos; risco recalculado com `app.comandos.recalcular` (26 s). Ambiente: container com 4 CPUs, tudo na mesma máquina, requisições pelo gateway, 20 repetições por rota (a primeira descartada).

| Rota | p50 | p95 | Meta 300 ms |
|---|---|---|---|
| `GET /academico/turmas`, `/disciplinas`, `/alunos`, `/inscricoes`, `/avaliacoes`, `/frequencias` (limite 20) | 10–11 ms | 11–14 ms | ✅ |
| `GET /academico/alunos?pagina=100` | 11 ms | 15 ms | ✅ |
| `GET /academico/alunos?busca=...` (`ILIKE`, varredura sequencial) | 15 ms | 17 ms | ✅ |
| `GET /auth/auditoria` (limite 20, com e sem filtro) | 14–21 ms | 15–24 ms | ✅ |
| `GET /analitico/apoio`, `/copiloto/sugestoes` | 8–9 ms | 11 ms | ✅ |
| `GET /analitico/alertas` | 2.633 ms | 2.833 ms | ❌ |
| `GET /analitico/painel` | 3.154 ms | 3.266 ms | ❌ |
| `GET /analitico/predicao` | 3.142 ms | 3.374 ms | ❌ |
| `GET /analitico/cenarios/projecao` | 3.223 ms | 3.390 ms | ❌ |
| `GET /analitico/relatorios/inscricoes` | 3.629 ms | 3.759 ms | ❌ |

**Leitura:**

- **Buscas e listagens paginadas (o que o RNF10 pede) ficam bem abaixo de 300 ms**, mesmo com 3 mil alunos.
- **As rotas agregadas do analítico não.** O gargalo é o previsto na D20: cada consulta busca todas as inscrições do recorte no acadêmico (`/internal/inscricoes`). Com 9.108 inscrições isso é 9,2 MB de JSON: 1,8 s só na resposta HTTP e 2,5 s com a validação Pydantic, o que explica quase todo o tempo de 3 s. O custo cresce linearmente (cerca de 0,34 ms por inscrição), então a meta de 300 ms seria ultrapassada a partir de ~900 inscrições (~300 alunos com 3 disciplinas). Na demonstração (108 inscrições) o painel respondeu em ~130 ms (log de auditoria).
- Esses números são de uma máquina de teste; servem para comparar rotas e ver a tendência, não como valor absoluto.

**Planos (`EXPLAIN ANALYZE`):**

| Consulta | Plano | Tempo |
|---|---|---|
| `resultado_risco WHERE inscricao_id ORDER BY id DESC LIMIT 1` | Index Scan Backward em `ix_resultado_risco_inscricao_id_id`, sem Sort | 0,08 ms |
| `log_requisicao WHERE usuario_id = 3 ORDER BY timestamp DESC LIMIT 20` | Index Scan Backward em `ix_log_requisicao_timestamp` | 0,16 ms |
| `log_requisicao WHERE status_http = 500 ORDER BY timestamp DESC LIMIT 20` | idem | 0,20 ms |
| `log_requisicao WHERE status_http BETWEEN 400 AND 499 ...` | idem | 0,10 ms |
| `aluno WHERE nome_completo ILIKE '%...%' ORDER BY nome_completo` | Seq Scan + Sort | 1,3 ms |

Ressalva: nos dados de `log_requisicao` gerados as colunas são distribuídas de modo uniforme; com tráfego real, o planejador pode escolher os índices `(usuario_id, timestamp)` e `(status_http, timestamp)` em vez do de `timestamp`. O índice trigram da busca por nome continua desnecessário nesta escala (1,3 ms com 3 mil alunos).

**Próximo passo sugerido:** atacar o gargalo da D20 guardando um resumo por inscrição no analítico (atualizado pelo worker a cada evento), ou então um endpoint de agregação no acadêmico, em vez de trazer todas as inscrições a cada consulta. Só vale a pena se a escala real passar de algumas centenas de alunos.

## Como repetir a medição

O roteiro abaixo foi seguido na medição acima.

### 1. Subir e popular

```bash
docker compose up --build -d
docker compose exec academico python -m app.comandos.seed
```

O seed é pequeno. Para medir de verdade, multiplique: crie algumas centenas de alunos, milhares de
inscrições e notas, e gere carga na auditoria (cada requisição vira uma linha em `log_requisicao`).

### 2. Tempo das listagens (meta do RNF: abaixo de 300 ms)

O tempo de resposta de cada requisição já fica em `log_requisicao.tempo_resposta_ms`. Depois de usar a
interface por alguns minutos, no `psql` do `auth_db`:

```sql
SELECT rota, count(*), round(avg(tempo_resposta_ms)) AS media_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY tempo_resposta_ms) AS p95_ms
FROM log_requisicao
WHERE metodo_http = 'GET'
GROUP BY rota
ORDER BY p95_ms DESC;
```

### 3. Plano das consultas

No `psql` do banco de cada serviço, com `EXPLAIN (ANALYZE, BUFFERS)`. Procure `Index Scan` ou `Index Only Scan`
com o índice esperado e a ausência de `Sort`:

```sql
-- analitico_db
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM resultado_risco WHERE inscricao_id = 1 ORDER BY id DESC LIMIT 1;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM acompanhamento WHERE aluno_id = 1 ORDER BY data DESC, id DESC;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM solicitacao_apoio WHERE estado = 'recebida' ORDER BY id DESC;

-- auth_db
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM log_requisicao WHERE usuario_id = 7 ORDER BY timestamp DESC LIMIT 20;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM log_requisicao WHERE status_http = 500 ORDER BY timestamp DESC LIMIT 20;
```

Com poucas linhas o PostgreSQL pode preferir varredura sequencial (é mais barata); o plano só importa depois
de popular. Rode `ANALYZE;` antes.

### 4. Pontos que podem precisar de ação depois de medir

- **Busca por nome de aluno** (`ILIKE '%termo%'`): o índice comum não atende curinga no início. Se a
  medição mostrar lentidão com muitos alunos, o caminho é um índice trigram (`pg_trgm`, extensão do
  PostgreSQL), que não foi adicionado por não dar para testar a migração sem o banco.
- **Filtro por classe de status** (`status_http BETWEEN 400 AND 499` ordenado por `timestamp`): o índice
  `(status_http, timestamp)` reduz as linhas, mas o PostgreSQL ainda ordena o resultado. Se pesar, o caminho
  é particionar `log_requisicao` por mês ou limitar a janela de tempo padrão da consulta.
- **`/internal/inscricoes`** carrega as inscrições com notas e frequências do recorte a cada consulta do
  painel (D20). Se a medição mostrar o painel lento, o caminho é o que a D20 já prevê: guardar um resumo
  por inscrição no analítico.
