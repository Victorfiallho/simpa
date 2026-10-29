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

  return (
    <svg className="anel" width="104" height="104" viewBox="0 0 104 104" role="img" aria-label={`${Math.round(percentual)}% ${legenda}`}>
      <circle cx="52" cy="52" r={raio} fill="none" stroke="rgb(255 255 255 / 0.55)" strokeWidth="12" />
      <circle
        cx="52"
        cy="52"
        r={raio}
        fill="none"
        stroke={cor}
        strokeWidth="12"
        strokeLinecap="round"
        strokeDasharray={`${preenchido} ${circunferencia}`}
        transform="rotate(-90 52 52)"
      />
      <text x="52" y="52" textAnchor="middle" fontSize="18" fontWeight="700" fill="#1d1d1b">
        {Math.round(percentual)}%
      </text>
      <text x="52" y="68" textAnchor="middle" fontSize="10" fill="rgb(29 29 27 / 0.65)">
        {legenda}
      </text>
    </svg>
  );
}
