// Tipos das respostas da API. Decimais chegam como texto ("7.50") para não perder precisão (D18).

export type Situacao = 'em_risco' | 'atencao' | 'sem_risco' | 'indeterminado';
export type Role = 'admin' | 'coordenador' | 'professor';
export type Decimal = string | null;

export interface Resposta<T> {
  status: 'sucesso' | 'erro';
  mensagem: string;
  dados: T;
  erro: { codigo: string; mensagem: string } | null;
}

export interface RespostaPaginada<T> extends Resposta<T[]> {
  pagina: number;
  limite: number;
  total_registros: number;
}

export interface Usuario {
  id: number;
  nome_usuario: string;
  role: Role;
}

export interface Token {
  access_token: string;
  expira_em_minutos: number;
  usuario: Usuario;
}

export interface Turma {
  id: number;
  codigo: string | null;
  nome: string;
  periodo_letivo: string;
  status: string;
}

export interface InscricaoPainel {
  inscricao_id: number;
  disciplina_id: number;
  disciplina_codigo: string | null;
  disciplina_nome: string;
  nota_n1: Decimal;
  nota_n2: Decimal;
  media: Decimal;
  frequencia: Decimal;
  aulas: number;
  faltas: number;
  status: string;
  atencao: boolean;
  situacao: Situacao;
  criterios: string[];
  justificativa: string;
}

export interface Achado {
  gravidade: 'alerta' | 'atencao' | 'info';
  titulo: string;
  texto: string;
}

export interface Recomendacao {
  prioridade: 'alta' | 'media' | 'baixa';
  disciplina: string | null;
  acao: string;
  motivo: string;
}

export interface AlunoPainel {
  id: number;
  nome: string;
  matricula: string;
  turma_id: number;
  turma_nome: string;
  media: Decimal;
  frequencia: Decimal;
  situacao: Situacao;
  inscricoes: InscricaoPainel[];
  recomendacoes: Recomendacao[];
}

export interface Painel {
  total_alunos: number;
  total_inscricoes: number;
  inscricoes_sem_dados: number;
  media_geral: Decimal;
  media_n1: Decimal;
  frequencia_geral: Decimal;
  frequencia_n1: Decimal;
  contagem: Record<Situacao, number>;
  histograma: { faixa: string; inscricoes: number }[];
  dispersao: { aluno: string; disciplina: string; media: string; frequencia: string; situacao: Situacao }[];
  correlacao_frequencia_media: Decimal;
  situacao_por_oferta: ({ oferta: string; disciplina_id: number } & Record<Situacao, number>)[];
  achados: Achado[];
  alunos: AlunoPainel[];
}

export interface ResumoEstatistico {
  n: number;
  media: Decimal;
  mediana: Decimal;
  variancia: Decimal;
  desvio_padrao: Decimal;
  minimo: Decimal;
  maximo: Decimal;
  tipo_variancia: 'populacional' | 'amostral';
  observacao: string | null;
}

export interface Indicadores {
  recorte: string;
  janela: 'acumulado' | 'N1';
  inscricoes_validas: number;
  inscricoes_sem_dados: number;
  media: ResumoEstatistico;
  frequencia: ResumoEstatistico;
  correlacao_frequencia_media: Decimal;
  histograma: { faixa: string; inscricoes: number }[];
  por_disciplina: {
    disciplina_id: number;
    oferta: string;
    disciplina: string;
    turma: string;
    n: number;
    media: Decimal;
    media_n1: Decimal;
    frequencia_media: Decimal;
  }[];
  situacao_alunos: Record<Situacao, number>;
  situacao_inscricoes: Record<Situacao, number>;
  achados: Achado[];
}

export interface Predicao {
  modelo: {
    equacao: string;
    variaveis: string[];
    coeficientes: number[];
    n: number;
    r2: number;
    erro_medio: number;
    erro_validacao: number;
    acerto_risco: number;
    interpretacao: string[];
  } | null;
  observacao: string | null;
  previsoes: {
    inscricao_id: number;
    aluno_id: number;
    aluno: string;
    matricula: string;
    disciplina: string;
    nota_n1: string;
    frequencia_n1: string;
    nota_n2_prevista: string;
    nota_n2_real: Decimal;
    media_projetada: string;
    media_real: Decimal;
    situacao_atual: Situacao;
    risco_projetado: boolean;
  }[];
  limites: string[];
}

export interface ResultadoRisco {
  id: number;
  inscricao_id: number;
  media_final: Decimal;
  frequencia_final: Decimal;
  status: string;
  atencao: boolean;
  criterios_violados: string;
  justificativa: string;
  calculado_em: string;
}
