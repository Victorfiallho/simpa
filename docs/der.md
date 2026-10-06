# DER — Diagrama Entidade-Relacionamento do SIMPA

Baseado no SRS v1.0.0 e nas decisões registradas em [`decisoes.md`](decisoes.md).

```mermaid
erDiagram
    USUARIO {
        int id PK
        string nome_usuario UK
        string email UK
        string senha_hash "bcrypt/argon2, nunca texto puro"
        string role "admin | coordenador | professor"
        bool ativo
        datetime criado_em
    }
    TURMA {
        int id PK
        string codigo UK "opcional"
        string nome
        string curso
        string periodo_letivo "ex.: 2026.2"
        string turno
        string sala
        string status "ativa | inativa | encerrada"
    }
    DISCIPLINA {
        int id PK
        string codigo UK "opcional"
        string nome
        int carga_horaria
        string periodo_letivo
        int turma_id FK
        int professor_id FK "Usuario com role professor"
        string status "ativa | inativa | encerrada"
    }
    ALUNO {
        int id PK
        string matricula UK "numero de matricula"
        string nome_completo
        string cpf UK "opcional"
        string email
        string telefone "opcional"
        date data_nascimento "opcional"
        string curso
        int turma_id FK "turma de origem"
        string status "ativo | inativo | transferido | concluido | evadido"
    }
    INSCRICAO {
        int id PK
        int aluno_id FK
        int disciplina_id FK
        string status "ativa | trancada | concluida | cancelada"
        datetime criado_em
    }
    AVALIACAO {
        int id PK
        int inscricao_id FK
        string tipo_avaliacao "prova | trabalho | atividade..."
        string periodo_avaliacao "ex.: N1, N2"
        decimal nota "0.00 a 10.00"
        decimal peso "maior que 0"
        datetime atualizado_em
    }
    FREQUENCIA {
        int id PK
        int inscricao_id FK
        string periodo_avaliacao
        int aulas_previstas "maior que 0"
        int faltas "0 ate aulas_previstas"
    }
    RESULTADO_RISCO {
        int id PK
        int inscricao_id FK
        decimal media_final
        decimal frequencia_final
        string status "em_risco | sem_risco | indeterminado"
        bool atencao
        string criterios_violados "media_baixa, frequencia_baixa"
        string justificativa
        datetime calculado_em
    }
    LOG_REQUISICAO {
        int id PK
        string correlation_id UK
        int usuario_id FK "nulo se anonimo"
        string rota
        string metodo_http
        int status_http
        string ip_origem
        int tempo_resposta_ms
        datetime timestamp
    }

    TURMA      ||--o{ ALUNO           : "agrupa"
    TURMA      ||--o{ DISCIPLINA      : "oferta"
    USUARIO    |o--o{ DISCIPLINA      : "leciona"
    ALUNO      ||--o{ INSCRICAO       : "se inscreve"
    DISCIPLINA ||--o{ INSCRICAO       : "recebe"
    INSCRICAO  ||--o{ AVALIACAO       : "possui"
    INSCRICAO  ||--o{ FREQUENCIA      : "possui"
    INSCRICAO  ||--o{ RESULTADO_RISCO : "gera historico"
    USUARIO    |o--o{ LOG_REQUISICAO  : "origina"
```

## Como ler as cardinalidades

| Símbolo | Significado |
|---|---|
| `\|\|` | exatamente um (obrigatório) |
| `\|o` | zero ou um (opcional) |
| `o{` | zero ou muitos |

Exemplo: `TURMA ||--o{ ALUNO` significa que todo aluno pertence a exatamente uma turma e que uma turma tem zero ou mais alunos.

## Restrições que o banco deve garantir (RNF08)

| Tabela | Restrição | Origem |
|---|---|---|
| aluno | `UNIQUE(matricula)`, `UNIQUE(cpf)` (permite nulo) | RF01 |
| turma, disciplina | `UNIQUE(codigo)` (permite nulo) | RF02 |
| usuario | `UNIQUE(email)`, `UNIQUE(nome_usuario)` | RF09 |
| inscricao | `UNIQUE(aluno_id, disciplina_id)` | D01 |
| avaliacao | `CHECK(nota BETWEEN 0 AND 10)`, `CHECK(peso > 0)` | RF03 |
| frequencia | `CHECK(aulas_previstas > 0)`, `CHECK(faltas BETWEEN 0 AND aulas_previstas)`, `UNIQUE(inscricao_id, periodo_avaliacao)` | RF03, D02 |
| todas as FKs | `ON DELETE RESTRICT` (sem exclusão física com histórico) | Restrição 3 |

## O que fica de fora do banco (e por quê)

- **Indicadores estatísticos (RF05):** são calculados sob demanda no `services/`. Guardá-los criaria dados duplicados que podem ficar desatualizados.
- **`frequencia_percentual`:** é derivado de `faltas` e `aulas_previstas` (D02).
- **`ResultadoRisco`** é a exceção. Ele é persistido porque o RF07 exige registrar o critério violado, e o histórico permite ver a evolução do aluno.

## Regras que o banco NÃO garante sozinho (ficam no service)

- Não lançar nota ou frequência em uma disciplina ou turma `encerrada` (D10).
- Só o professor da disciplina pode lançar notas nela (D03).
- Recalcular o `ResultadoRisco` a cada alteração de avaliação ou frequência (RF03).
- Validar a sintaxe do CPF (dígitos verificadores) (RF01).
