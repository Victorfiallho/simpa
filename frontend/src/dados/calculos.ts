// Regras de cálculo do SIMPA (RF05, RF07, D04–D09). Espelham o que o serviço analítico
// fará no backend; quando a API existir, a tela passa a só exibir o resultado.

import type { Aluno, Avaliacao, Criterio, Disciplina, Inscricao, Status } from './tipos';

export const MEDIA_MINIMA = 600;
export const FREQUENCIA_MINIMA = 7500;
export const MEDIA_ATENCAO = 700;
export const FREQUENCIA_ATENCAO = 8000;

/** Divisão inteira com arredondamento HALF_UP, para valores não negativos (D06). */
export function dividirArredondando(numerador: number, denominador: number): number {
  return Math.floor((2 * numerador + denominador) / (2 * denominador));
}

export function mediaPonderada(avaliacoes: Avaliacao[]): number | null {
  const pesos = avaliacoes.reduce((soma, a) => soma + a.peso, 0);
  if (pesos === 0) return null;
  return dividirArredondando(
    avaliacoes.reduce((soma, a) => soma + a.nota * a.peso, 0),
    pesos,
  );
}

export function percentualDePresenca(aulas: number, faltas: number): number | null {
  return aulas === 0 ? null : dividirArredondando((aulas - faltas) * 10000, aulas);
}

/** Classificação da inscrição. "Atenção" é um sinal sobre Sem risco (D08). */
export function classificar(media: number | null, frequencia: number | null): Status {
  if (media === null || frequencia === null) return 'indeterminado';
  if (media < MEDIA_MINIMA || frequencia < FREQUENCIA_MINIMA) return 'em_risco';
  if (media < MEDIA_ATENCAO || frequencia < FREQUENCIA_ATENCAO) return 'atencao';
  return 'sem_risco';
}

export interface ResumoInscricao {
  inscricao: Inscricao;
  disciplina: Disciplina;
  notaN1: number | null;
  notaN2: number | null;
  media: number | null;
  mediaN1: number | null;
  frequencia: number | null;
  aulas: number;
  faltas: number;
  status: Status;
  criterios: Criterio[];
}

export function resumirInscricao(inscricao: Inscricao, disciplina: Disciplina): ResumoInscricao {
  const aulas = inscricao.frequencias.reduce((soma, f) => soma + f.aulas, 0);
  const faltas = inscricao.frequencias.reduce((soma, f) => soma + f.faltas, 0);
  const media = mediaPonderada(inscricao.avaliacoes);
  const frequencia = percentualDePresenca(aulas, faltas);
  const status = classificar(media, frequencia);

  const criterios: Criterio[] = [];
  if (status === 'em_risco') {
    if (media !== null && media < MEDIA_MINIMA) criterios.push('media_baixa');
    if (frequencia !== null && frequencia < FREQUENCIA_MINIMA) criterios.push('frequencia_baixa');
  }

  const nota = (periodo: 'N1' | 'N2') =>
    inscricao.avaliacoes.find((a) => a.periodo === periodo)?.nota ?? null;

  return {
    inscricao,
    disciplina,
    notaN1: nota('N1'),
    notaN2: nota('N2'),
    media,
    mediaN1: mediaPonderada(inscricao.avaliacoes.filter((a) => a.periodo === 'N1')),
    frequencia,
    aulas,
    faltas,
    status,
    criterios,
  };
}

// Qualquer disciplina em risco torna o aluno Em risco (D04). Sem risco conhecido, uma
// disciplina sem dados torna o aluno Indeterminado; depois vêm Atenção e Sem risco.
const PRECEDENCIA: Status[] = ['em_risco', 'indeterminado', 'atencao', 'sem_risco'];

export interface AlunoConsolidado extends Aluno {
  resumos: ResumoInscricao[];
  status: Status;
  media: number | null;
  frequencia: number | null;
}

export function mediaSimples(valores: (number | null)[]): number | null {
  const validos = valores.filter((v): v is number => v !== null);
  if (validos.length === 0) return null;
  return dividirArredondando(
    validos.reduce((soma, v) => soma + v, 0),
    validos.length,
  );
}

export function consolidarAluno(aluno: Aluno, resumos: ResumoInscricao[]): AlunoConsolidado {
  const validos = resumos.filter((r) => r.status !== 'indeterminado');
  return {
    ...aluno,
    resumos,
    status: PRECEDENCIA.find((s) => resumos.some((r) => r.status === s)) ?? 'indeterminado',
    media: mediaSimples(validos.map((r) => r.media)),
    frequencia: mediaSimples(validos.map((r) => r.frequencia)),
  };
}
