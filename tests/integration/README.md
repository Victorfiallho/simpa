# Testes entre serviços

HTTP e RabbitMQ reais, sem mocks, contra o ambiente isolado `simpa-test` (`compose.test.yml`).
Não importam os pacotes `app` dos serviços: só falam com o gateway e controlam o Docker Compose.

## Preparar

```bash
cp .env.test.example .env.test          # credenciais sintéticas; o .env.test não vai para o Git
python3 -m venv .venv-integracao && .venv-integracao/bin/pip install -r tests/integration/requirements.txt
docker compose --env-file .env.test -p simpa-test -f compose.test.yml up -d --build --wait --wait-timeout 180
```

O gateway de teste fica em `127.0.0.1:18080`; PostgreSQL e RabbitMQ não são publicados no host.

## Rodar

```bash
.venv-integracao/bin/python -m pytest tests/integration -q
```

Os testes marcados `interrupcao` (`pytest -m interrupcao`) derrubam e religam o worker, o broker e o
acadêmico. Eles religam tudo no `finally`, mesmo se uma asserção falhar, mas **não rodam em paralelo**
com outros testes. Sem `-p xdist` (não instalado), o pytest já roda em série.

## Limpar

```bash
docker compose --env-file .env.test -p simpa-test -f compose.test.yml down       # mantém os volumes
docker compose --env-file .env.test -p simpa-test -f compose.test.yml down -v    # apaga SÓ o projeto simpa-test
```

Sempre com `-p simpa-test` e `-f compose.test.yml`. Nunca rode `down -v` sem o projeto explícito.
