// Notas em centésimos (0 a 1000 = 0,00 a 10,00) e frequência em centésimos de ponto
// percentual (0 a 10000 = 0,00% a 100,00%). Inteiros evitam erro de arredondamento (D06).

export type Turma = 'A' | 'B';
export type Status = 'em_risco' | 'atencao' | 'sem_risco' | 'indeterminado';
export type Criterio = 'media_baixa' | 'frequencia_baixa';

export interface Aluno {
  id: number;
  nome: string;
  matricula: string;
  turma: Turma;
}

export interface Disciplina {
  id: number;
  nome: string;
  sigla: string;
}

export interface Avaliacao {
  periodo: 'N1' | 'N2';
  nota: number;
  peso: number;
}

export interface FrequenciaSemanal {
  semana: number;
  aulas: number;
  faltas: number;
}

export interface Inscricao {
  id: number;
  alunoId: number;
  disciplinaId: number;
  avaliacoes: Avaliacao[];
  frequencias: FrequenciaSemanal[];
}

export interface BaseAcademica {
  periodoLetivo: string;
  semanas: number;
  alunos: Aluno[];
  disciplinas: Disciplina[];
  inscricoes: Inscricao[];
}
