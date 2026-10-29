"""Popula o SIMPA com dados 100% sintéticos, pela própria API (RNF04, ROADMAP 1.7).

Uso (com o Docker rodando):
    docker compose exec academico python -m app.comandos.seed

Entra como admin no auth, descobre os professores de demonstração e cadastra 2 turmas,
6 disciplinas, 36 alunos, 108 inscrições, notas N1/N2 e frequências. Inclui de propósito:
média baixa, frequência baixa, as fronteiras 6,00 / 75,00% e uma inscrição sem dados (D09).
Se a turma A já existir, não faz nada (pode rodar mais de uma vez).
"""

import os
import random
import sys
import unicodedata

import httpx

from app.core.config import get_settings

API = "http://localhost:8000"
PERIODO = "2026.2"
AULAS_POR_PERIODO = 32

NOMES = [
    "Ana Beatriz Lima", "Bruno Henrique Costa", "Camila Rodrigues", "Daniel Oliveira",
    "Eduarda Martins", "Felipe Almeida", "Gabriela Santos", "Henrique Souza",
    "Isabela Ferreira", "João Pedro Silva", "Karina Mendes", "Lucas Ribeiro",
    "Mariana Barbosa", "Nicolas Araújo", "Olívia Cardoso", "Paulo Vitor Dias",
    "Rafaela Nunes", "Samuel Rocha", "Talita Fernandes", "Vinícius Pereira",
    "Alice Monteiro", "Bernardo Melo", "Clara Azevedo", "Davi Teixeira",
    "Elisa Carvalho", "Francisco Moura", "Giovana Castro", "Heitor Freitas",
    "Íris Andrade", "Júlia Batista", "Leonardo Cunha", "Manuela Ramos",
    "Otávio Lopes", "Pedro Rezende", "Sofia Duarte", "Thiago Vieira",
]  # fmt: skip

DISCIPLINAS = [
    ("EST", "Estatística Aplicada", 0.0),
    ("POO", "Programação Orientada a Objetos", 0.25),
    ("ALG", "Álgebra Linear", -0.4),
]

# Casos de propósito: (índice do aluno, sigla) → (nota N1, nota N2, faltas N1, faltas N2).
# None nas notas = inscrição sem nenhum lançamento (status Indeterminado, D09).
CASOS_ESPECIAIS = {
    (4, "EST"): (6.0, 6.0, 8, 8),  # fronteira exata: média 6,00 e frequência 75,00%
    (5, "ALG"): (3.5, 4.5, 2, 3),  # média baixa
    (6, "POO"): (7.5, 8.0, 12, 12),  # frequência baixa: 62,50%
    (7, "EST"): (None, None, None, None),  # sem dados
    (8, "ALG"): (5.98, 6.0, 1, 2),  # média 5,992 → 5,99: em risco por pouco (D06)
}


def gerar_cpf(aleatorio: random.Random) -> str:
    digitos = [aleatorio.randint(0, 9) for _ in range(9)]
    for tamanho in (9, 10):
        soma = sum(d * p for d, p in zip(digitos, range(tamanho + 1, 1, -1), strict=True))
        digitos.append(soma * 10 % 11 % 10)
    return "".join(map(str, digitos))


def nota(valor: float) -> float:
    """Nota de 0 a 10 com uma casa decimal, como o professor lança."""
    return round(min(10.0, max(0.0, valor)), 1)


def sortear_faltas(aleatorio: random.Random, assiduidade: float) -> int:
    return sum(aleatorio.random() > assiduidade for _ in range(AULAS_POR_PERIODO))


def email_de(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    partes = sem_acento.lower().split()
    return f"{partes[0]}.{partes[-1]}@aluno.simpa.dev"


class Api:
    def __init__(self, token: str):
        self.cliente = httpx.Client(
            base_url=API, headers={"Authorization": f"Bearer {token}"}, timeout=20
        )

    def get(self, rota: str, **params) -> dict:
        return self._verificar(self.cliente.get(rota, params=params))

    def post(self, rota: str, corpo: dict) -> dict:
        return self._verificar(self.cliente.post(rota, json=corpo))["dados"]

    @staticmethod
    def _verificar(resposta: httpx.Response) -> dict:
        if resposta.is_error:
            sys.exit(f"Falha em {resposta.request.url}: {resposta.status_code} {resposta.text}")
        return resposta.json()


def entrar() -> tuple[str, list[int]]:
    senha = os.environ.get("DEMO_SENHA")
    if not senha:
        sys.exit("Defina DEMO_SENHA no .env (é a senha dos usuários de demonstração).")
    auth = get_settings().auth_url
    resposta = httpx.post(
        f"{auth}/login", json={"email": "admin@simpa.dev", "senha": senha}, timeout=20
    )
    if resposta.is_error:
        sys.exit(f"Não foi possível entrar como admin: {resposta.text}")
    professores = httpx.get(f"{auth}/internal/usuarios", params={"role": "professor"}).json()
    ids = [p["id"] for p in professores["dados"]]
    if len(ids) < len(DISCIPLINAS):
        sys.exit("Faltam professores de demonstração no auth (USUARIOS_DEMO=true).")
    return resposta.json()["dados"]["access_token"], ids


def main() -> None:
    token, professores = entrar()
    api = Api(token)
    if api.get("/turmas", codigo=f"IA2-{PERIODO}-A")["total_registros"]:
        print("O banco já tem os dados de demonstração. Nada a fazer.")
        return

    # Semente fixa: os mesmos dados em toda execução. Não é uso criptográfico.
    aleatorio = random.Random(2026)  # noqa: S311
    total = {"turmas": 0, "disciplinas": 0, "alunos": 0, "inscricoes": 0, "notas": 0, "freq": 0}

    for letra, turno in (("A", "noturno"), ("B", "matutino")):
        turma = api.post(
            "/turmas",
            {
                "codigo": f"IA2-{PERIODO}-{letra}",
                "nome": f"IA · 2º período {letra}",
                "curso": "Inteligência Artificial",
                "periodo_letivo": PERIODO,
                "turno": turno,
                "sala": f"Bloco C · {letra}2",
            },
        )
        total["turmas"] += 1

        disciplinas = {}
        for (sigla, nome, dificuldade), professor in zip(DISCIPLINAS, professores, strict=False):
            disciplinas[sigla] = (
                api.post(
                    "/disciplinas",
                    {
                        "codigo": f"{sigla}-{PERIODO}-{letra}",
                        "nome": nome,
                        "carga_horaria": 64,
                        "periodo_letivo": PERIODO,
                        "turma_id": turma["id"],
                        "professor_id": professor,
                    },
                ),
                dificuldade,
            )
            total["disciplinas"] += 1

        inicio = 0 if letra == "A" else 18
        for indice in range(inicio, inicio + 18):
            nome = NOMES[indice]
            aluno = api.post(
                "/alunos",
                {
                    "matricula": f"2026{indice + 1:04d}",
                    "nome_completo": nome,
                    "cpf": gerar_cpf(aleatorio) if indice % 3 else None,
                    "email": email_de(nome),
                    "curso": "Inteligência Artificial",
                    "turma_id": turma["id"],
                },
            )
            total["alunos"] += 1
            habilidade = aleatorio.gauss(7.4, 1.0)
            assiduidade = min(1.0, max(0.62, aleatorio.gauss(0.9, 0.055)))

            for sigla, (disciplina, dificuldade) in disciplinas.items():
                inscricao = api.post(
                    "/inscricoes", {"aluno_id": aluno["id"], "disciplina_id": disciplina["id"]}
                )
                total["inscricoes"] += 1

                nivel = habilidade + dificuldade + aleatorio.gauss(0, 0.45)
                n1, n2, f1, f2 = CASOS_ESPECIAIS.get(
                    (indice, sigla),
                    (
                        nota(nivel + aleatorio.gauss(-0.1, 0.6)),
                        nota(nivel + aleatorio.gauss(0.15, 0.6)),
                        sortear_faltas(aleatorio, assiduidade),
                        sortear_faltas(aleatorio, assiduidade),
                    ),
                )
                if n1 is None:
                    continue
                for periodo, valor, peso, falta in (("N1", n1, 4, f1), ("N2", n2, 6, f2)):
                    api.post(
                        "/avaliacoes",
                        {
                            "inscricao_id": inscricao["id"],
                            "tipo_avaliacao": "prova",
                            "periodo_avaliacao": periodo,
                            "nota": f"{valor:.2f}",
                            "peso": str(peso),
                        },
                    )
                    api.post(
                        "/frequencias",
                        {
                            "inscricao_id": inscricao["id"],
                            "periodo_avaliacao": periodo,
                            "aulas_previstas": AULAS_POR_PERIODO,
                            "faltas": falta,
                        },
                    )
                    total["notas"] += 1
                    total["freq"] += 1

    print(
        "Dados de demonstração criados: "
        f"{total['turmas']} turmas, {total['disciplinas']} disciplinas, {total['alunos']} alunos, "
        f"{total['inscricoes']} inscrições, {total['notas']} notas e {total['freq']} frequências."
    )


if __name__ == "__main__":
    main()
