"""Fluxo principal entre serviços, sem mocks (etapa 4.2 do plano de qualidade).

HTTP → acadêmico (banco) → RabbitMQ → worker do analítico → banco analítico → HTTP.
"""

from __future__ import annotations

from decimal import Decimal

from tests.integration import suporte
from tests.integration.suporte import dados, esperar_ate


def test_do_lancamento_ao_relatorio(admin, coordenacao, prof_ana):
    # 1 e 2. Login (admin, que cadastra e lança) e cadastros.
    turma = suporte.criar_turma(admin)
    disciplina = suporte.criar_disciplina(admin, turma["id"], prof_ana.usuario_id)
    aluno = suporte.criar_aluno(admin, turma["id"])
    inscricao = suporte.inscrever(admin, aluno["id"], disciplina["id"])

    # 3. Nota baixa e frequência boa: o risco vem da média (D04, D06).
    nota = suporte.lancar_nota(admin, inscricao["id"], "4.00")
    suporte.lancar_frequencia(admin, inscricao["id"], faltas=2)  # 30/32 = 93,75%

    # 4. O histórico chega pelo broker e pelo worker, sem espera fixa.
    historico = esperar_ate(
        lambda: suporte.historico(admin, inscricao["id"]),
        lambda h: any(r["status"] == "em_risco" and r["media_final"] == "4.00" for r in h),
        "histórico com a inscrição em risco e média 4,00",
    )
    assert {r["inscricao_id"] for r in historico} == {inscricao["id"]}
    em_risco = historico[-1]
    assert em_risco["status"] == "em_risco"
    assert Decimal(em_risco["media_final"]) == Decimal("4.00")
    assert em_risco["criterios_violados"] == "media_baixa"
    assert Decimal(em_risco["frequencia_final"]) == Decimal("93.75")

    # 5. A nota sobe: a condição de risco deixa de existir.
    dados(admin.patch(f"/academico/avaliacoes/{nota['id']}", {"nota": "8.00"}))

    # 6. A transição aparece, uma única vez, com os valores novos. O `indeterminado` inicial
    # (inscrição ainda sem notas, D09) é opcional: o recálculo parte do estado ATUAL, então, se
    # o evento da inscrição for processado depois do lançamento, o histórico começa em `em_risco`.
    historico = esperar_ate(
        lambda: suporte.historico(admin, inscricao["id"]),
        lambda h: bool(h) and h[-1]["status"] == "sem_risco",
        "transição de em_risco para sem_risco",
    )
    sequencia = suporte.estados(historico)
    assert sequencia[-2:] == ["em_risco", "sem_risco"]
    assert sequencia in (["em_risco", "sem_risco"], ["indeterminado", "em_risco", "sem_risco"])
    assert [r["status"] for r in historico].count("sem_risco") == 1
    atual = historico[-1]
    assert Decimal(atual["media_final"]) == Decimal("8.00")
    assert Decimal(atual["frequencia_final"]) == Decimal("93.75")
    assert atual["criterios_violados"] == ""

    # 7. O relatório mostra a situação nova, com o e-mail mascarado (LGPD).
    resposta = coordenacao.get(
        "/analitico/relatorios/inscricoes", params={"formato": "csv", "turma_id": turma["id"]}
    )
    assert resposta.status_code == 200, resposta.text[:300]
    assert resposta.headers["content-type"].startswith("text/csv")
    linhas = suporte.ler_relatorio_csv(resposta.content)
    assert [linha["Matrícula"] for linha in linhas] == [aluno["matricula"]]
    linha = linhas[0]
    assert linha["Aluno"] == aluno["nome_completo"]
    assert linha["Disciplina"] == disciplina["nome"]
    assert linha["Situação"] == "Sem risco"
    assert (linha["N1"], linha["Média"], linha["Frequência (%)"]) == ("8,00", "8,00", "93,75")
    assert aluno["email"] not in resposta.text
