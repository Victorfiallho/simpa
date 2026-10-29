import type { ReactNode } from 'react';

interface Props {
  icone: ReactNode;
  titulo: string;
  descricao: string;
}

export function EmBreve({ icone, titulo, descricao }: Props) {
  return (
    <div className="em-breve">
      <span className="icone-grande">{icone}</span>
      <h2>{titulo}</h2>
      <p>{descricao}</p>
    </div>
  );
}
