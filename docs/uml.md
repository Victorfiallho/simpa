# Diagramas UML do SIMPA

Diagramas exigidos pelo RNF05. Estão em [Mermaid](https://mermaid.js.org/), que o GitHub desenha direto na página; para editar, basta mudar o texto.

## Casos de uso

O Mermaid não tem um diagrama de casos de uso próprio; a convenção aqui é a usual: atores à esquerda, casos de uso em elipses agrupados pelo serviço que os atende, e as linhas ligam cada ator ao que ele pode fazer (tabela de perfis da D03).

```mermaid
flowchart LR
    admin(["Ator: Administrador"])
    coord(["Ator: Coordenador"])
    prof(["Ator: Professor"])
    sistema(["Ator: Serviço analítico"])

    subgraph auth[Serviço auth]
        uc1([Entrar no sistema])
        uc2([Gerenciar usuários])
    end

    subgraph academico[Serviço acadêmico]
        uc3([Cadastrar turmas e disciplinas])
        uc4([Cadastrar alunos])
        uc5([Inscrever aluno em disciplina])
        uc6([Lançar notas])
        uc7([Lançar frequência])
        uc8([Consultar aluno])
        uc9([Encerrar turma ou disciplina])
        uc10([Reabrir turma ou disciplina])
    end

    subgraph analitico[Serviço analítico]
        uc11([Consultar indicadores])
        uc12([Consultar risco e justificativa])
        uc13([Exportar relatórios])
        uc14([Recalcular risco da inscrição])
    end

    admin --- uc1 & uc2 & uc3 & uc4 & uc5 & uc6 & uc7 & uc8 & uc9 & uc10 & uc11 & uc12 & uc13
    coord --- uc1 & uc3 & uc4 & uc5 & uc8 & uc9 & uc11 & uc12 & uc13
    prof --- uc1 & uc6 & uc7 & uc8 & uc11 & uc12
    uc6 & uc7 -. "«include» evento" .-> uc14
    sistema --- uc14
```

| Caso de uso | Requisito | Estado |
|---|---|---|
| Entrar no sistema | RF09 | Pronto (`POST /api/auth/login`) |
| Gerenciar usuários | RF09 | Fase 3 (hoje só os usuários de demonstração) |
| Cadastrar turmas, disciplinas e alunos | RF01, RF02 | Pronto |
| Inscrever aluno em disciplina | RF03, D01 | Pronto |
| Lançar notas e frequência | RF03, D02 | Pronto |
| Consultar aluno | RF04 | Pronto (sem indicadores, que vêm na Fase 2) |
| Encerrar e reabrir | D10 | Pronto (reabrir só o admin) |
| Indicadores, risco e relatórios | RF05–RF07, RF11 | Fase 2 |
| Recalcular risco da inscrição | RF03, D11 | Evento chega ao worker; cálculo na Fase 2 |

As restrições "professor só nas próprias disciplinas" e "só admin gerencia usuários" (D03) entram na Fase 3.

## Classes

Classes de domínio de cada serviço, com os atributos do DER e as operações dos services. As associações entre serviços diferentes são só por id (D13).

```mermaid
classDiagram
    direction LR

    namespace auth {
        class Usuario {
            +int id
            +str nome_usuario
            +str email
            -str senha_hash
            +str role
            +bool ativo
            +autenticar(email, senha) Token
        }
        class LogRequisicao {
            +int id
            +str correlation_id
            +int usuario_id
            +str rota
            +int status_http
            +int tempo_resposta_ms
        }
    }

    namespace academico {
        class Turma {
            +int id
            +str codigo
            +str nome
            +str periodo_letivo
            +str turno
            +str status
        }
        class Disciplina {
            +int id
            +str codigo
            +str nome
            +int carga_horaria
            +int professor_id
            +str status
            +encerrada() bool
        }
        class Aluno {
            +int id
            +str matricula
            +str nome_completo
            +str cpf
            +str email
            +str status
        }
        class Inscricao {
            +int id
            +str status
            +datetime criado_em
        }
        class Avaliacao {
            +int id
            +str tipo_avaliacao
            +str periodo_avaliacao
            +Decimal nota
            +Decimal peso
        }
        class Frequencia {
            +int id
            +str periodo_avaliacao
            +int aulas_previstas
            +int faltas
            +frequencia_percentual() Decimal
        }
    }

    namespace analitico {
        class ResultadoRisco {
            +int id
            +int inscricao_id
            +Decimal media_final
            +Decimal frequencia_final
            +str status
            +bool atencao
            +str criterios_violados
            +str justificativa
        }
    }

    Turma "1" --> "0..*" Disciplina : oferta
    Turma "1" --> "0..*" Aluno : agrupa
    Aluno "1" --> "0..*" Inscricao : se inscreve
    Disciplina "1" --> "0..*" Inscricao : recebe
    Inscricao "1" *-- "0..*" Avaliacao : possui
    Inscricao "1" *-- "0..*" Frequencia : possui
    Usuario "0..1" ..> "0..*" Disciplina : leciona (id)
    Inscricao "1" ..> "0..*" ResultadoRisco : histórico (id)
    Usuario "0..1" ..> "0..*" LogRequisicao : origina (id)
```

Linhas contínuas são FKs reais; linhas pontilhadas ligam serviços diferentes por id, sem FK (D13).

## Camadas de cada serviço

Todos os serviços seguem a mesma divisão. A seta indica "chama":

```mermaid
flowchart LR
    api["api/<br/>rotas HTTP"] --> services["services/<br/>regras de negócio"]
    services --> repositories["repositories/<br/>consultas"]
    repositories --> models["models/<br/>tabelas"]
    api -. valida com .-> schemas["schemas/<br/>DTOs Pydantic"]
    services -. publica .-> events["events/<br/>RabbitMQ"]
    services -. chama .-> clientes["clientes/<br/>outros serviços"]
```
