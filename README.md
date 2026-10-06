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

# 3. Dependências
pip install -r requirements.txt

# 4. Configuração
cp .env.example .env             # Windows: copy .env.example .env

# 5. Verificar
ruff check .
pytest
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

- [Decisões técnicas](docs/decisoes.md)
- [DER](docs/der.md)

## Equipe

| Integrante | Responsabilidades |
|---|---|
| | |
