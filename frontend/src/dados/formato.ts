import type { Criterio, Status } from './tipos';

const DUAS_CASAS = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const UMA_CASA = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export const ROTULO_STATUS: Record<Status, string> = {
  em_risco: 'Em risco',
  atencao: 'Atenção',
  sem_risco: 'Sem risco',
  indeterminado: 'Indeterminado',
};

export const ORDEM_STATUS: Status[] = ['em_risco', 'atencao', 'indeterminado', 'sem_risco'];

export const COR_STATUS: Record<Status, string> = {
  em_risco: '#ea7957',
  atencao: '#e1ba58',
  sem_risco: '#8ca573',
  indeterminado: '#7a80f0',
};

/** 640 → "6,40" */
export function formatarNota(centesimos: number | null): string {
  return centesimos === null ? '—' : DUAS_CASAS.format(centesimos / 100);
}

/** 8125 → "81,25%" */
export function formatarPercentual(centesimos: number | null): string {
  return centesimos === null ? '—' : `${DUAS_CASAS.format(centesimos / 100)}%`;
}

export function formatarDecimal(valor: number, casas: 1 | 2 = 1): string {
  return (casas === 1 ? UMA_CASA : DUAS_CASAS).format(valor);
}

export function iniciais(nome: string): string {
  const partes = nome.split(' ');
  return `${partes[0][0]}${partes[partes.length - 1][0]}`.toUpperCase();
}

export function descreverCriterio(
  criterio: Criterio,
  media: number | null,
  frequencia: number | null,
): string {
  return criterio === 'media_baixa'
    ? `média ${formatarNota(media)} abaixo de 6,00`
    : `frequência ${formatarPercentual(frequencia)} abaixo de 75%`;
}
