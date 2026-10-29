-- Um banco por serviço (D13). Roda só na primeira subida, com o volume do Postgres vazio.
-- Para recriar do zero: docker compose down -v
CREATE DATABASE auth_db;
CREATE DATABASE academico_db;
CREATE DATABASE analitico_db;
