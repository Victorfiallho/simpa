// Tipos das respostas da API. Decimais chegam como texto ("7.50") para não perder precisão (D18).

export type Situacao = 'em_risco' | 'atencao' | 'sem_risco' | 'indeterminado';
export type Role = 'admin' | 'coordenador' | 'professor' | 'aluno';
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

// ---------- Alertas e acompanhamento (RF07) ----------

export type TipoAlerta = 'queda' | 'frequencia' | 'abandono';
export type NivelAlerta = 'atencao' | 'alto';
export type EstadoAtendimento = 'pendente' | 'acomp' | 'encerrado';
export type TipoAcompanhamento = 'contato' | 'orientacao' | 'monitoria';

export interface Alerta {
  aluno_id: number;
  aluno_nome: string;
  matricula: string;
  disciplina_id: number;
  disciplina_nome: string;
  professor_id: number | null;
  tipo: TipoAlerta;
  nivel: NivelAlerta;
  titulo: string;
  detalhe: string;
  acao_sugerida: string;
  estado: EstadoAtendimento;
  ultimo_contato: string;
}

export interface ResumoTipoAlerta {
  tipo: TipoAlerta;
  total: number;
  graves: number;
  pendentes: number;
}

export interface ListaAlertas {
  resumo: ResumoTipoAlerta[];
  alertas: Alerta[];
}

export interface Acompanhamento {
  id: number;
  aluno_id: number;
  disciplina_id: number | null;
  tipo: TipoAcompanhamento;
  data: string;
  responsavel: string;
  observacao: string;
  revisao: string | null;
  revisao_feita: boolean;
  revisao_vencida: boolean;
}

// ---------- Cenários (RF07) ----------

export type BaseCenario = 'n1' | 'atual';

export interface MargemCenario {
  inscricao_id: number;
  aluno_id: number;
  aluno_nome: string;
  matricula: string;
  disciplina_id: number;
  disciplina_nome: string;
  modo: 'sem_dados' | 'n2' | 'aprovado' | 'exame' | 'rep_nota';
  n1: Decimal;
  n2: Decimal;
  media: Decimal;
  frequencia: Decimal;
  necessario: Decimal;
  media_maxima: Decimal;
  viabilidade: string;
  gravidade: number;
  meta: string;
  hipotese_media: Decimal | null;
  hipotese_resultado: string | null;
}

export interface ProjecaoCenario {
  regras: { aprovacao: string; recuperacao: string; final: string };
  base: BaseCenario;
  inscricoes_projetadas: number;
  contagem: { direta: number; recuperacao: number; rep_nota: number; rep_freq: number; sem_dados: number };
  retencao_percentual: Decimal;
  alunos: { aprovados_em_tudo: number; com_recuperacao: number; com_reprovacao: number };
  por_oferta: { oferta: string; direta: number; recuperacao: number; rep_nota: number; rep_freq: number }[];
  variacao_por_disciplina: { disciplina_id: number; disciplina_nome: string; variacao: string }[];
  total_metas: number;
  metas: MargemCenario[];
}

// ---------- Auditoria (RF12) ----------

export interface RegistroAuditoria {
  id: number;
  correlation_id: string;
  usuario_id: number | null;
  rota: string;
  metodo_http: string;
  status_http: number;
  ip_origem: string;
  tempo_resposta_ms: number;
  timestamp: string;
}

// ---------- Copiloto (RF07) ----------

export interface RespostaCopiloto {
  intencao: string;
  recorte: string;
  texto: string;
  itens: { aluno_id: number; aluno_nome: string; matricula: string; detalhe: string }[];
  total_itens: number;
  secoes: { titulo: string; linhas: string[] }[];
  texto_completo: string | null;
  sugestoes: string[];
}

export type EstadoApoio = 'recebida' | 'atendimento' | 'concluida';

export interface Solicitacao {
  id: number;
  aluno_id: number;
  disciplina_id: number | null;
  motivo: string;
  texto: string;
  estado: EstadoApoio;
  criada_em: string;
  atualizada_em: string;
  historico: { estado: EstadoApoio; em: string }[];
}

export interface SolicitacaoDaCoordenacao extends Solicitacao {
  aluno_nome: string | null;
  matricula: string | null;
  disciplina_nome: string | null;
}

export interface Perfil {
  usuario_id: number;
  nome_usuario: string;
  role: Role;
  aluno_id: number | null;
  nome_completo: string | null;
  telefone: string | null;
  email_contato: string | null;
  cidade: string | null;
  uf: string | null;
  tem_foto: boolean;
  preenchimento_percentual: number;
}
