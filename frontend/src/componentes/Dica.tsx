// Caixa exibida ao passar o mouse sobre os gráficos (Recharts).

interface Item {
  name?: string | number;
  value?: number | string | (number | string)[];
  color?: string;
  fill?: string;
}

interface Props {
  active?: boolean;
  payload?: Item[];
  label?: string | number;
  formatar?: (valor: number) => string;
  nomes?: Record<string, string>;
}

export function Dica({ active, payload, label, formatar = String, nomes = {} }: Props) {
  if (!active || !payload?.length) return null;
  return (
    <div className="dica">
      <strong>{label}</strong>
      {payload
        .filter((item) => typeof item.value === 'number')
        .map((item) => (
          <div key={String(item.name)}>
            <span className="ponto" style={{ color: item.color ?? item.fill }} />
            {nomes[String(item.name)] ?? item.name}:{' '}
            <span className="num">{formatar(item.value as number)}</span>
          </div>
        ))}
    </div>
  );
}
