"""Schemas de saída do serviço analítico.

Decimais saem como texto ("7.50"), como no acadêmico (D18).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InscricaoPainel(BaseModel):
    inscricao_id: int
    disciplina_id: int
    disciplina_codigo: str | None
    disciplina_nome: str
    nota_n1: Decimal | None
    nota_n2: Decimal | None
    media: Decimal | None
    frequencia: Decimal | None
    aulas: int
    faltas: int
    status: str
    atencao: bool
    situacao: str
    criterios: list[str]
    justificativa: str


class AchadoSaida(BaseModel):
    """Padrão detectado nos dados, descrito em uma frase (interpretação automática)."""

    model_config = ConfigDict(from_attributes=True)

    gravidade: str
    titulo: str
    texto: str


class RecomendacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prioridade: str
    disciplina: str | None
    acao: str
    motivo: str


class AlunoPainel(BaseModel):
    id: int
    nome: str
    matricula: str
    turma_id: int
    turma_nome: str
    media: Decimal | None
    frequencia: Decimal | None
    status: str
    atencao: bool
    situacao: str
    inscricoes: list[InscricaoPainel]
    recomendacoes: list[RecomendacaoSaida] = []


class FaixaHistograma(BaseModel):
    faixa: str
    inscricoes: int


class PontoDispersao(BaseModel):
    aluno: str
    disciplina: str
    media: Decimal
    frequencia: Decimal
    situacao: str


class SituacaoOferta(BaseModel):
    oferta: str
    disciplina_id: int
    em_risco: int
    atencao: int
    sem_risco: int
    indeterminado: int


class Painel(BaseModel):
    """Tudo o que a Visão geral e a tela de Alunos exibem, numa única chamada."""

    total_alunos: int
    total_inscricoes: int
    inscricoes_sem_dados: int
    media_geral: Decimal | None
    media_n1: Decimal | None
    frequencia_geral: Decimal | None
    frequencia_n1: Decimal | None
    contagem: dict[str, int]
    histograma: list[FaixaHistograma]
    dispersao: list[PontoDispersao]
    correlacao_frequencia_media: Decimal | None
    situacao_por_oferta: list[SituacaoOferta]
    achados: list[AchadoSaida]
    alunos: list[AlunoPainel]


class ResumoEstatistico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    n: int
    media: Decimal | None
    mediana: Decimal | None
    variancia: Decimal | None
    desvio_padrao: Decimal | None
    minimo: Decimal | None
    maximo: Decimal | None
    tipo_variancia: str
    observacao: str | None


class IndicadorDisciplina(BaseModel):
    disciplina_id: int
    oferta: str
    disciplina: str
    turma: str
    n: int
    media: Decimal | None
    media_n1: Decimal | None
    frequencia_media: Decimal | None


class Indicadores(BaseModel):
    """Indicadores estatísticos de um recorte (RF05)."""

    recorte: str
    janela: str
    inscricoes_validas: int
    inscricoes_sem_dados: int
    media: ResumoEstatistico
    frequencia: ResumoEstatistico
    correlacao_frequencia_media: Decimal | None
    histograma: list[FaixaHistograma]
    por_disciplina: list[IndicadorDisciplina]
    situacao_alunos: dict[str, int]
    situacao_inscricoes: dict[str, int]
    achados: list[AchadoSaida]


class ModeloRegressao(BaseModel):
    equacao: str
    variaveis: list[str]
    coeficientes: list[float]
    n: int
    r2: float
    erro_medio: float
    erro_validacao: float
    acerto_risco: float
    interpretacao: list[str]


class PrevisaoInscricao(BaseModel):
    inscricao_id: int
    aluno_id: int
    aluno: str
    matricula: str
    disciplina: str
    nota_n1: Decimal
    frequencia_n1: Decimal
    nota_n2_prevista: Decimal
    nota_n2_real: Decimal | None
    media_projetada: Decimal
    media_real: Decimal | None
    situacao_atual: str
    risco_projetado: bool


class Predicao(BaseModel):
    """Regressão linear N2 ~ N1 + frequência N1 e projeção da média final (Nível 2, D21)."""

    modelo: ModeloRegressao | None
    observacao: str | None
    previsoes: list[PrevisaoInscricao]
    limites: list[str]


class ResultadoRiscoLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inscricao_id: int
    media_final: Decimal | None
    frequencia_final: Decimal | None
    status: str
    atencao: bool
    criterios_violados: str
    justificativa: str
    calculado_em: datetime
