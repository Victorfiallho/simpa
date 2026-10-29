// Monta tudo o que as telas exibem a partir da base acadêmica e do filtro de turma.

import {
  type AlunoConsolidado,
  consolidarAluno,
  mediaSimples,
  percentualDePresenca,
  type ResumoInscricao,
  resumirInscricao,
} from './calculos';
import type { BaseAcademica, Status, Turma } from './tipos';

export type FiltroTurma = 'todas' | Turma;

export interface Painel {
  periodoLetivo: string;
  alunos: AlunoConsolidado[];
  totalInscricoes: number;
  mediaGeral: number | null;
  mediaGeralN1: number | null;
  frequenciaGeral: number | null;
  frequenciaRecente: number | null;
  histograma: { faixa: string; inscricoes: number }[];
  frequenciaSemanal: { semana: string; A: number | null; B: number | null }[];
  situacaoPorOferta: ({ oferta: string } & Record<Status, number>)[];
  contagem: Record<Status, number>;
}

const SEMANAS_RECENTES = 4;

function presencaNasSemanas(resumos: ResumoInscricao[], de: number, ate: number): number | null {
  const semanas = resumos.flatMap((r) =>
    r.inscricao.frequencias.filter((f) => f.semana >= de && f.semana <= ate),
  );
  return percentualDePresenca(
    semanas.reduce((soma, f) => soma + f.aulas, 0),
    semanas.reduce((soma, f) => soma + f.faltas, 0),
  );
}

export function montarPainel(base: BaseAcademica, turma: FiltroTurma): Painel {
  const disciplinaPorId = new Map(base.disciplinas.map((d) => [d.id, d]));
  const alunosDoRecorte = base.alunos.filter((a) => turma === 'todas' || a.turma === turma);

  const alunos = alunosDoRecorte.map((aluno) =>
    consolidarAluno(
      aluno,
      base.inscricoes
        .filter((i) => i.alunoId === aluno.id)
        .map((i) => resumirInscricao(i, disciplinaPorId.get(i.disciplinaId)!)),
    ),
  );
  const resumos = alunos.flatMap((a) => a.resumos);
  const validos = resumos.filter((r) => r.status !== 'indeterminado');

  // Histograma das médias por inscrição, em faixas de 1 ponto (a última inclui o 10).
  const histograma = Array.from({ length: 10 }, (_, i) => ({
    faixa: `${i}–${i + 1}`,
    inscricoes: validos.filter((r) => Math.min(9, Math.floor(r.media! / 100)) === i).length,
  }));

  const turmaDoAluno = new Map(alunos.map((a) => [a.id, a.turma]));
  const frequenciaSemanal = Array.from({ length: base.semanas }, (_, i) => {
    const semana = i + 1;
    const daTurma = (t: Turma) => {
      const doGrupo = resumos.filter((r) => turmaDoAluno.get(r.inscricao.alunoId) === t);
      const valor = doGrupo.length ? presencaNasSemanas(doGrupo, semana, semana) : null;
      return valor === null ? null : valor / 100;
    };
    return { semana: `S${semana}`, A: daTurma('A'), B: daTurma('B') };
  });

  const turmas: Turma[] = turma === 'todas' ? ['A', 'B'] : [turma];
  const situacaoPorOferta = base.disciplinas.flatMap((disciplina) =>
    turmas.map((t) => {
      const daOferta = resumos.filter(
        (r) => r.disciplina.id === disciplina.id && turmaDoAluno.get(r.inscricao.alunoId) === t,
      );
      const contar = (s: Status) => daOferta.filter((r) => r.status === s).length;
      return {
        oferta: `${disciplina.sigla} ${t}`,
        em_risco: contar('em_risco'),
        atencao: contar('atencao'),
        sem_risco: contar('sem_risco'),
        indeterminado: contar('indeterminado'),
      };
    }),
  );

  const contar = (s: Status) => alunos.filter((a) => a.status === s).length;

  return {
    periodoLetivo: base.periodoLetivo,
    alunos,
    totalInscricoes: resumos.length,
    mediaGeral: mediaSimples(validos.map((r) => r.media)),
    mediaGeralN1: mediaSimples(validos.map((r) => r.mediaN1)),
    frequenciaGeral: mediaSimples(validos.map((r) => r.frequencia)),
    frequenciaRecente: presencaNasSemanas(
      validos,
      base.semanas - SEMANAS_RECENTES + 1,
      base.semanas,
    ),
    histograma,
    frequenciaSemanal,
    situacaoPorOferta,
    contagem: {
      em_risco: contar('em_risco'),
      atencao: contar('atencao'),
      sem_risco: contar('sem_risco'),
      indeterminado: contar('indeterminado'),
    },
  };
}
