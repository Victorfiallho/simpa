"""Prova de ponta a ponta: backup, origem parada, restauração e conferência.

Roda só nos ambientes descartáveis (origem `simpa-test`, destino `simpa-restore-test`).

  uv run --no-project --with httpx --with cryptography python \\
      scripts/backup/provar_restauracao.py --chave K --pasta P --relatorio R.json

Etapas e o que cada uma prova:
 1. Cria dados novos e reconhecíveis na origem, pela API, e espera o evento chegar ao histórico.
 2. Guarda uma "fotografia" de referência: JWKS, relatório de inscrições, notas e histórico.
 3. Faz o backup (mede a duração).
 4. Cria um dado DEPOIS do backup (marcador). Ele não pode existir no restaurado: mostra o ponto de
    recuperação (a perda real do RPO) em vez de esconder.
 5. PARA a origem (não apaga o volume) para que o restaurado não possa "colar" nela.
 6. Restaura em ambiente vazio e sobe a aplicação (mede o tempo até o login funcionar: RTO medido).
 7. Confere: chaves (JWKS igual; token emitido na origem continua válido), usuários, relatório e
    histórico idênticos, marcador ausente, e uma mudança nova é processada pelo worker.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import criar_backup
import cripto
import httpx
import restaurar_backup
from ambiente import RAIZ, Compose

sys.path.insert(0, str(RAIZ / "tests" / "integration"))
import suporte  # noqa: E402

ORIGEM = Compose("simpa-test", RAIZ / "compose.test.yml", RAIZ / ".env.test")
DESTINO = Compose(
    "simpa-restore-test", RAIZ / "compose.restore-test.yml", RAIZ / ".env.restore-test"
)
URL_ORIGEM = "http://127.0.0.1:18080"
URL_DESTINO = "http://127.0.0.1:18081"


def esperar_saude(c: Compose, prazo: float = 300) -> None:
    limite = time.monotonic() + prazo
    while time.monotonic() < limite:
        saida = c.rodar("ps", "-a", "--format", "json").stdout.decode()
        estados = [json.loads(ln) for ln in saida.splitlines() if ln.strip()]
        if estados and all(
            (e.get("Health") or e.get("State")) in ("healthy", "running") for e in estados
        ):
            if all(e.get("Health") != "starting" for e in estados):
                return
        time.sleep(3)
    raise SystemExit(f"{c.projeto} não ficou saudável em {prazo}s")


def fotografia(http: httpx.Client, gestor: suporte.Sessao, inscricoes: list[int]) -> dict:
    relatorio = gestor.get("/analitico/relatorios/inscricoes", params={"formato": "csv"})
    if relatorio.status_code != 200:
        raise SystemExit(f"relatório falhou: {relatorio.text[:300]}")
    linhas = suporte.ler_relatorio_csv(relatorio.content)
    return {
        "jwks": http.get("/api/auth/.well-known/jwks.json").json(),
        "relatorio": sorted(linhas, key=lambda x: json.dumps(x, sort_keys=True)),
        "avaliacoes": {
            i: suporte.dados(gestor.get("/academico/avaliacoes", params={"inscricao_id": i}))
            for i in inscricoes
        },
        "historico": {
            i: [{k: v for k, v in h.items() if k != "id"} for h in suporte.historico(gestor, i)]
            for i in inscricoes
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chave", type=Path, required=True)
    ap.add_argument("--pasta", type=Path, required=True)
    ap.add_argument("--relatorio", type=Path, required=True)
    a = ap.parse_args()
    chave = cripto.ler_chave(a.chave)
    senha = suporte.ler_env()["DEMO_SENHA"]
    relatorio: dict = {"verificacoes": {}}

    def ok(nome: str, condicao: bool, detalhe: str = "") -> None:
        relatorio["verificacoes"][nome] = {"ok": bool(condicao), "detalhe": detalhe}
        print(("OK    " if condicao else "FALHA ") + nome + (f" ({detalhe})" if detalhe else ""))

    origem = httpx.Client(base_url=URL_ORIGEM, timeout=30)
    gestor = suporte.entrar(origem, "admin@simpa.dev", senha)
    professor = suporte.entrar(origem, "ana.prof@simpa.dev", senha)
    token_da_origem = gestor.token

    # 1-2. Dados de referência e fotografia.
    turma = suporte.criar_turma(gestor)
    disciplina = suporte.criar_disciplina(gestor, turma["id"], professor.usuario_id, "Restauração")
    inscricoes: list[int] = []
    for nota, faltas in (("3.0", 12), ("9.0", 0), ("5.5", 6)):
        aluno = suporte.criar_aluno(gestor, turma["id"])
        insc = suporte.inscrever(gestor, aluno["id"], disciplina["id"])
        suporte.lancar_nota(gestor, insc["id"], nota)
        suporte.lancar_frequencia(gestor, insc["id"], faltas)
        inscricoes.append(insc["id"])
    for i in inscricoes:
        suporte.esperar_ate(
            lambda i=i: suporte.historico(gestor, i), bool, f"histórico da inscrição {i}", 30
        )
    antes = fotografia(origem, gestor, inscricoes)

    # 3. Backup.
    inicio_backup = time.monotonic()
    pacote, manifesto = criar_backup.criar(ORIGEM, chave, a.pasta)
    relatorio["backup"] = {
        "pacote": pacote.name,
        "tamanho_bytes": pacote.stat().st_size,
        "duracao_s": round(time.monotonic() - inicio_backup, 1),
        "janela_sem_escrita_s": manifesto["janela_sem_escrita_s"],
        "criado_em_utc": manifesto["criado_em_utc"],
    }
    esperar_saude(ORIGEM)

    # 4. Dado posterior ao backup.
    gestor = suporte.entrar(origem, "admin@simpa.dev", senha)
    aluno_pos = suporte.criar_aluno(gestor, turma["id"])
    marcador = aluno_pos["matricula"]

    # 5. Origem parada (volumes preservados).
    ORIGEM.rodar("stop")

    # 6. Restauração e subida: tempo total desde o início é o RTO medido nesta prova.
    inicio_rto = time.monotonic()
    restaurar_backup.validar_destino("simpa-restore-test", "simpa-restore-test")
    import tempfile  # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="simpa-restore-") as tmp:
        man = restaurar_backup.abrir_pacote(pacote, chave, Path(tmp))
        tempos = restaurar_backup.restaurar(DESTINO, man)
    DESTINO.rodar("up", "-d")
    esperar_saude(DESTINO)
    destino = httpx.Client(base_url=URL_DESTINO, timeout=30)
    gestor_d = suporte.entrar(destino, "admin@simpa.dev", senha)
    relatorio["restauracao"] = {
        "tempos_s": tempos,
        "rto_medido_s": round(time.monotonic() - inicio_rto, 1),
    }

    # 7. Conferências.
    ok(
        "chave de assinatura: JWKS idêntico ao da origem",
        antes["jwks"] == destino.get("/api/auth/.well-known/jwks.json").json(),
    )
    resposta = httpx.get(
        f"{URL_DESTINO}/api/academico/alunos",
        headers={"Authorization": f"Bearer {token_da_origem}"},
    )
    ok(
        "token emitido na origem é aceito pelo restaurado",
        resposta.status_code == 200,
        str(resposta.status_code),
    )
    ok(
        "usuários restaurados fazem login (admin e professor)",
        bool(suporte.entrar(destino, "ana.prof@simpa.dev", senha)),
    )
    depois = fotografia(destino, gestor_d, inscricoes)
    ok(
        "relatório de inscrições idêntico",
        antes["relatorio"] == depois["relatorio"],
        f"{len(depois['relatorio'])} linhas",
    )
    ok("notas idênticas", antes["avaliacoes"] == depois["avaliacoes"])
    ok("histórico de risco idêntico", antes["historico"] == depois["historico"])
    achado = suporte.dados(gestor_d.get("/academico/alunos", params={"busca": marcador}))
    ok(
        "dado criado depois do backup NÃO existe (ponto de recuperação)",
        not achado,
        f"matrícula {marcador}",
    )
    antes_n = len(suporte.historico(gestor_d, inscricoes[0]))
    suporte.lancar_nota(gestor_d, inscricoes[0], "9.5", periodo="N2", peso="6")
    try:
        suporte.esperar_ate(
            lambda: len(suporte.historico(gestor_d, inscricoes[0])),
            lambda n: n > antes_n,
            "novo evento",
            40,
        )
        processou = True
    except AssertionError:
        processou = False
    ok("mudança nova no restaurado é processada pelo worker", processou)

    # Encerra o destino sem apagar volumes e religa a origem.
    DESTINO.rodar("down")
    ORIGEM.rodar("start", check=False)
    esperar_saude(ORIGEM)
    relatorio["resultado"] = (
        "APROVADO" if all(v["ok"] for v in relatorio["verificacoes"].values()) else "REPROVADO"
    )
    a.relatorio.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(relatorio["backup"] | relatorio["restauracao"], indent=2), relatorio["resultado"]
    )
    return 0 if relatorio["resultado"] == "APROVADO" else 1


if __name__ == "__main__":
    sys.exit(main())
