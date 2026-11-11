import { useNumeroAnimado } from '../movimento';

/**
 * Número que conta até o valor quando o dado chega ou muda. O texto final é o mesmo do valor
 * estático; só o caminho até ele é animado.
 */
export function NumeroAnimado({
  valor,
  formatar,
}: {
  valor: number | string | null | undefined;
  formatar: (n: number) => string;
}) {
  const numero = valor === null || valor === undefined || valor === '' ? null : Number(valor);
  const atual = useNumeroAnimado(numero !== null && Number.isFinite(numero) ? numero : null);
  return <>{atual === null ? '—' : formatar(atual)}</>;
}
