import type { Decimal, Situacao } from '../api/tipos';

const DUAS_CASAS = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const ROTULO_SITUACAO: Record<Situacao, string> = {
  em_risco: 'Em risco',
  atencao: 'Atenção',
  sem_risco: 'Sem risco',
  indeterminado: 'Indeterminado',
};

export const ORDEM_SITUACAO: Situacao[] = ['em_risco', 'atencao', 'indeterminado', 'sem_risco'];

export const COR_SITUACAO: Record<Situacao, string> = {
  em_risco: '#ea7957',
  atencao: '#e1ba58',
  sem_risco: '#8ca573',
  indeterminado: '#7a80f0',
};

/** "7.5" → 7.5; nulo continua nulo. */
export function numero(valor: Decimal | undefined): number | null {
  return valor === null || valor === undefined ? null : Number(valor);
}

/** "6.4" → "6,40" */
export function formatarNota(valor: Decimal | number | undefined): string {
  return valor === null || valor === undefined ? '—' : DUAS_CASAS.format(Number(valor));
}

/** "81.25" → "81,25%" */
export function formatarPercentual(valor: Decimal | number | undefined): string {
  return valor === null || valor === undefined ? '—' : `${DUAS_CASAS.format(Number(valor))}%`;
}

export function iniciais(nome: string): string {
  const partes = nome.split(' ');
  return `${partes[0][0]}${partes[partes.length - 1][0]}`.toUpperCase();
}

export function formatarDataHora(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}
