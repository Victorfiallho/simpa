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

## O que ainda não foi feito: medir

Nada foi medido em PostgreSQL com volume. Os números abaixo precisam de Docker.

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
