# SIMPA — Sistema Inteligente de Monitoramento e Predição Acadêmica

Projeto Integrador — 2º período de Inteligência Artificial — UniEVANGÉLICA.

Plataforma para registrar notas e frequência, calcular indicadores estatísticos, classificar risco acadêmico com justificativa e expor tudo por meio de uma API REST segura.

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI + Pydantic |
| Persistência | SQLAlchemy + Alembic (SQLite em dev) |
| Análise | pandas / numpy / matplotlib |
| Qualidade | pytest + ruff |

## Como rodar

```bash
# 1. Clonar e entrar
git clone <url-do-repo> && cd simpa

# 2. Ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Dependências (inclui pytest, ruff e httpx)
pip install -r requirements-dev.txt

# 4. Configuração — depois edite o JWT_SECRET no .env
cp .env.example .env             # Windows: copy .env.example .env

# 5. Banco de dados
alembic upgrade head

# 6. Verificar
ruff check .
pytest
```

> `requirements.txt` tem só o necessário para rodar a aplicação.
> `requirements-dev.txt` acrescenta as ferramentas de teste e lint.

### Gerar uma migração depois de alterar os models

```bash
alembic revision --autogenerate -m "descricao curta"
alembic upgrade head
```

## Estrutura

```
app/
  core/          configuração, banco, segurança, exceções, logs
  models/        entidades (tabelas do banco)
  schemas/       DTOs de entrada/saída e validação (Pydantic)
  repositories/  acesso a dados — único lugar que fala com o banco
  services/      regras de negócio: estatística, risco, relatórios
  api/           rotas HTTP (controllers)
migrations/      migrações do Alembic
tests/
  unit/          testes de services (sem banco)
  integration/   testes de rotas da API
docs/            SRS, DER, decisões técnicas, diagramas UML
scripts/         seed de dados sintéticos
```

## Documentação

- [Especificação de Requisitos (SRS v1.0.0)](docs/srs-v1.0.0.docx)
- [Enunciado do Projeto Integrador](docs/enunciado-pi.pdf)
- [Decisões técnicas](docs/decisoes.md)
- [DER](docs/der.md)

## Equipe

| Integrante | Responsabilidades |
|---|---|
| _Nome_ | _ex.: API e autenticação_ |
| _Nome_ | _ex.: estatística e risco_ |
| _Nome_ | _ex.: relatórios e gráficos_ |
