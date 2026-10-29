FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /servico

# Nunca rodar a aplicação como root dentro do container.
RUN useradd --create-home --uid 1000 simpa

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Pasta usada pelo volume de chaves do auth; nos outros serviços fica vazia.
RUN mkdir -p chaves && chown -R simpa:simpa /servico

USER simpa
EXPOSE 8000

# Aplica as migrações e sobe a API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
