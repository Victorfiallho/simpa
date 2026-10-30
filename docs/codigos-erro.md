# Códigos de erro da API

Toda resposta da API tem o mesmo formato (RF10, RNF14). Em caso de erro, `status` vale `"erro"` e o objeto `erro` traz um **código interno** estável, que o frontend pode usar para decidir o que mostrar:

```json
{
  "status": "erro",
  "mensagem": "Dados inválidos na requisição.",
  "dados": null,
  "erro": {
    "codigo": "VALIDACAO",
    "mensagem": "Dados inválidos na requisição.",
    "campos": [
      { "campo": "cpf", "regra": "value_error", "mensagem": "CPF inválido: dígito verificador não confere." }
    ]
  }
}
```

`campos` só vem preenchido nos erros de validação: diz **qual campo**, **qual regra** foi violada e uma mensagem em português.

## Gerais (todos os serviços)

| HTTP | Código | Quando acontece |
|---|---|---|
| 401 | `NAO_AUTENTICADO` | Sem token, token inválido ou expirado; e-mail ou senha errados no login (mensagem genérica, RF09 CA01) |
| 403 | `ACESSO_NEGADO` | Perfil do usuário não permite a ação (tabela da D03) |
| 404 | `NAO_ENCONTRADO` | O recurso do caminho da URL não existe |
| 405 | `METODO_NAO_PERMITIDO` | Método HTTP não aceito na rota |
| 429 | `MUITAS_TENTATIVAS` | Login bloqueado por erros seguidos no mesmo e-mail (5 erros, 60 s; cabeçalho `Retry-After`) | RF09 |
| 409 | `CONFLITO` | O banco recusou o registro por uma regra de unicidade ou integridade não tratada antes |
| 422 | `VALIDACAO` | Corpo, query ou caminho fora do formato; veja `erro.campos` |
| 500 | `ERRO_INTERNO` | Erro inesperado. A resposta nunca traz stack trace; o detalhe fica no log, com o `X-Request-ID` |
| 503 | `SERVICO_INDISPONIVEL` | Um serviço do qual a operação depende não respondeu |

## Serviço acadêmico

| HTTP | Código | Quando acontece | Origem |
|---|---|---|---|
| 409 | `CODIGO_DUPLICADO` | Código de turma ou disciplina já usado | RF02 |
| 409 | `MATRICULA_DUPLICADA` | Matrícula já cadastrada | RF01 |
| 409 | `CPF_DUPLICADO` | CPF já cadastrado para outro aluno | RF01 |
| 409 | `INSCRICAO_DUPLICADA` | O aluno já está inscrito na disciplina | D01 |
| 409 | `FREQUENCIA_DUPLICADA` | Já existe frequência no mesmo período para a inscrição | D02 |
| 409 | `DISCIPLINA_ENCERRADA` | Lançamento em disciplina encerrada, ou em disciplina de turma encerrada | D10 |
| 409 | `TURMA_ENCERRADA` | Nova disciplina ou inativação em turma encerrada | D10 |
| 403 | `REABERTURA_RESTRITA` | Quem não é admin tentou reabrir turma ou disciplina encerrada | D10 |
| 403 | `DISCIPLINA_FORA_DO_ESCOPO` | Professor tentou acessar disciplina (ou inscrição, nota, frequência) de outro professor | D03 |
| 403 | `ALUNO_FORA_DO_ESCOPO` | Professor tentou consultar aluno sem inscrição nas suas disciplinas | D03 |
| 422 | `REFERENCIA_INVALIDA` | Id citado no corpo (turma, aluno, disciplina, inscrição) não existe | RNF08 |
| 422 | `PROFESSOR_INVALIDO` | `professor_id` não é de um professor ativo no auth | D03, D13 |
| 422 | `REGRAS_INVALIDAS` | Regras de cenário fora de 0 a 10, ou média de recuperação acima da de aprovação | RF07 |
| 422 | `ALUNO_INATIVO` | Inscrição de aluno que não está ativo | RF03 |
| 422 | `DISCIPLINA_INATIVA` | Inscrição em disciplina inativa | RF03 |
| 422 | `INSCRICAO_INATIVA` | Nota ou frequência em inscrição trancada, concluída ou cancelada | RF03 |
| 422 | `FALTAS_INVALIDAS` | Edição que deixaria as faltas maiores que as aulas previstas | D02 |
| 422 | `CAMPO_OBRIGATORIO` | PATCH tentando apagar (enviar `null`) um campo obrigatório | RF10 |
| 422 | `ORDENACAO_INVALIDA` | `ordenar_por` com um campo que não pode ser usado para ordenar | RF08 |

## Serviço auth

| HTTP | Código | Quando acontece | Origem |
|---|---|---|---|
| 409 | `USUARIO_DUPLICADO` | Nome de usuário ou e-mail já cadastrado | RF09 |

Para criar um código novo: crie a exceção com `codigo="..."` no service, acrescente uma linha aqui e um teste que confira o código.

## Perfil aluno e pedidos de apoio (analítico)

| HTTP | Código | Quando acontece | Origem |
|---|---|---|---|
| 409 | `LIMITE_DE_SOLICITACOES` | O aluno já tem 5 pedidos de apoio em aberto | RF07 |
| 422 | `MOTIVO_INVALIDO` | Motivo fora da lista de motivos do pedido de apoio | RF07 |
| 422 | `DISCIPLINA_NAO_INSCRITA` | Disciplina em que o aluno não está inscrito | RF07 |

## Copiloto (analítico)

O copiloto não tem códigos próprios: pergunta com menos de 2 ou mais de 300 caracteres, ou com campos extras, responde `422 VALIDACAO`. Uma pergunta que ele não entende **não é erro**: volta `200` com `intencao: "ajuda"` e as sugestões.

## Registro semanal (acadêmico)

| HTTP | Código | Quando acontece | Origem |
|---|---|---|---|
| 409 | `SEMANA_DUPLICADA` | Já existe registro da mesma semana para a inscrição | RF07 |
| 422 | `ENTREGAS_INVALIDAS` | Atividades entregues acima das previstas, ao atualizar | RF07 |
