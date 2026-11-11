import { m, useReducedMotion } from 'motion/react';

import { CURVA_SAIDA, useNumeroAnimado } from '../movimento';

interface Props {
  percentual: number;
  cor: string;
  legenda: string;
}

/** Anel de progresso dos blocos de situação. */
export function Anel({ percentual, cor, legenda }: Props) {
  const raio = 38;
  const circunferencia = 2 * Math.PI * raio;
  const preenchido = (Math.min(100, Math.max(0, percentual)) / 100) * circunferencia;
  const reduzido = useReducedMotion();
  const exibido = useNumeroAnimado(Math.round(percentual)) ?? 0;

  return (
    <svg className="anel" width="104" height="104" viewBox="0 0 104 104" role="img" aria-label={`${Math.round(percentual)}% ${legenda}`}>
      <circle cx="52" cy="52" r={raio} fill="none" stroke="rgb(255 255 255 / 0.55)" strokeWidth="12" />
      {/* Com 0% não há arco: a ponta arredondada desenharia um ponto solto. */}
      {preenchido > 0 && (
      <m.circle
        cx="52"
        cy="52"
        r={raio}
        fill="none"
        stroke={cor}
        strokeWidth="12"
        strokeLinecap="round"
        initial={reduzido ? false : { strokeDasharray: `0 ${circunferencia}` }}
        animate={{ strokeDasharray: `${preenchido} ${circunferencia}` }}
        transition={{ duration: 1, ease: CURVA_SAIDA, delay: 0.15 }}
        transform="rotate(-90 52 52)"
      />
      )}
      <text x="52" y="52" textAnchor="middle" fontSize="18" fontWeight="700" fill="#1d1d1b">
        {Math.round(exibido)}%
      </text>
      <text x="52" y="68" textAnchor="middle" fontSize="10" fill="rgb(29 29 27 / 0.65)">
        {legenda}
      </text>
    </svg>
  );
}
