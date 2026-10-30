"""Rotas do serviço analítico: painel, indicadores, histórico de risco e relatórios."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.clientes import academico
from app.core.database import get_db
from app.core.respostas import Resposta
from app.core.seguranca import UsuarioAtual, exigir_roles, usuario_atual
from app.schemas.analitico import Indicadores, Painel, Predicao, ResultadoRiscoLeitura
from app.services import escopo, relatorios
from app.services.painel import Janela, montar_indicadores, montar_painel, montar_predicao
from app.services.risco import historico

Usuario = Annotated[UsuarioAtual, Depends(usuario_atual)]
Sessao = Annotated[Session, Depends(get_db)]
Gestor = Annotated[UsuarioAtual, Depends(exigir_roles("admin", "coordenador"))]
JanelaQuery = Annotated[
    Janela, Query(description="acumulado (N1 + N2) ou N1 (parcial: variância amostral, D07)")
]
Situacao = Literal["em_risco", "atencao", "sem_risco", "indeterminado"]

painel = APIRouter(tags=["Painel"])
indicadores = APIRouter(prefix="/indicadores", tags=["Indicadores"])
riscos = APIRouter(prefix="/riscos", tags=["Risco"])
relatorio = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@painel.get("/painel", response_model=Resposta[Painel])
def obter_painel(usuario: Usuario, turma_id: int | None = None, periodo_letivo: str | None = None):
    """Indicadores, risco por aluno e dados dos gráficos da Visão geral, numa única chamada."""
    inscricoes = academico.buscar_inscricoes(turma_id=turma_id, periodo_letivo=periodo_letivo)
    inscricoes = escopo.filtrar_inscricoes(inscricoes, usuario)
    return Resposta[Painel](dados=montar_painel(inscricoes))


def _indicadores(
    inscricoes, recorte: str, janela: Janela, usuario: UsuarioAtual
) -> Resposta[Indicadores]:
    inscricoes = escopo.filtrar_inscricoes(inscricoes, usuario)
    return Resposta[Indicadores](dados=montar_indicadores(inscricoes, recorte, janela))


@painel.get("/predicao", response_model=Resposta[Predicao], tags=["Predição"])
def obter_predicao(
    usuario: Usuario, turma_id: int | None = None, periodo_letivo: str | None = None
):
    """Regressão linear N2 ~ N1 + frequência N1 e média final projetada (Nível 2, D21)."""
    inscricoes = academico.buscar_inscricoes(turma_id=turma_id, periodo_letivo=periodo_letivo)
    inscricoes = escopo.filtrar_inscricoes(inscricoes, usuario)
    return Resposta[Predicao](dados=montar_predicao(inscricoes))


@indicadores.get("/turmas/{turma_id}", response_model=Resposta[Indicadores])
def indicadores_da_turma(turma_id: int, usuario: Usuario, janela: JanelaQuery = "acumulado"):
    inscricoes = academico.buscar_inscricoes(turma_id=turma_id)
    return _indicadores(inscricoes, f"turma {turma_id}", janela, usuario)


@indicadores.get("/disciplinas/{disciplina_id}", response_model=Resposta[Indicadores])
def indicadores_da_disciplina(
    disciplina_id: int, usuario: Usuario, janela: JanelaQuery = "acumulado"
):
    inscricoes = academico.buscar_inscricoes(disciplina_id=disciplina_id)
    if inscricoes:
        escopo.garantir_disciplina_propria(inscricoes[0].disciplina.professor_id, usuario)
    return _indicadores(inscricoes, f"disciplina {disciplina_id}", janela, usuario)


@indicadores.get("/alunos/{aluno_id}", response_model=Resposta[Indicadores])
def indicadores_do_aluno(aluno_id: int, usuario: Usuario, janela: JanelaQuery = "acumulado"):
    inscricoes = academico.buscar_inscricoes(aluno_id=aluno_id)
    return _indicadores(inscricoes, f"aluno {aluno_id}", janela, usuario)


@indicadores.get("/periodos/{periodo_letivo}", response_model=Resposta[Indicadores])
def indicadores_do_periodo(
    periodo_letivo: str, usuario: Usuario, janela: JanelaQuery = "acumulado"
):
    inscricoes = academico.buscar_inscricoes(periodo_letivo=periodo_letivo)
    return _indicadores(inscricoes, f"período {periodo_letivo}", janela, usuario)


@riscos.get(
    "/inscricoes/{inscricao_id}/historico", response_model=Resposta[list[ResultadoRiscoLeitura]]
)
def historico_de_risco(inscricao_id: int, db: Sessao, usuario: Usuario):
    """Transições de classificação da inscrição, da mais recente para a mais antiga (D11)."""
    if usuario.role == "professor":
        inscricao = academico.buscar_inscricao(inscricao_id)
        escopo.garantir_disciplina_propria(inscricao.disciplina.professor_id, usuario)
    linhas = [ResultadoRiscoLeitura.model_validate(r) for r in historico(db, inscricao_id)]
    return Resposta[list[ResultadoRiscoLeitura]](dados=linhas)


@relatorio.get(
    "/inscricoes",
    response_class=Response,
    responses={200: {"description": "Arquivo do relatório (CSV, XLSX ou PDF)"}},
)
def relatorio_de_inscricoes(
    usuario: Gestor,
    formato: Literal["csv", "xlsx", "pdf"] = "csv",
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    periodo_letivo: str | None = None,
    situacao: Situacao | None = None,
):
    """Inscrições do recorte com notas, frequência, situação e justificativa (RF11)."""
    inscricoes = academico.buscar_inscricoes(
        turma_id=turma_id, disciplina_id=disciplina_id, periodo_letivo=periodo_letivo
    )
    filtros = ", ".join(
        f"{nome} = {valor}"
        for nome, valor in (
            ("turma", turma_id),
            ("disciplina", disciplina_id),
            ("período", periodo_letivo),
            ("situação", relatorios.ROTULO_SITUACAO.get(situacao or "", None)),
        )
        if valor is not None
    )
    emails = {i.aluno.id: i.aluno.email for i in inscricoes}
    conteudo = relatorios.montar(montar_painel(inscricoes), emails, usuario, filtros, situacao)
    gerar, tipo = relatorios.GERADORES[formato]
    nome = f"simpa-relatorio-{date.today():%Y-%m-%d}.{formato}"
    return Response(
        gerar(conteudo),
        media_type=tipo,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
