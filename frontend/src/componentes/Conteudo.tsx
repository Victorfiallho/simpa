import { TriangleAlert } from 'lucide-react';
import type { ReactNode } from 'react';

import type { Estado } from '../api/useDados';

/** Mostra carregamento, erro ou o conteúdo, para toda tela que busca dados. */
export function Conteudo<T>({
  estado,
  children,
}: {
  estado: Estado<T>;
  children: (dados: T) => ReactNode;
}) {
  if (estado.erro) {
    return (
      <div className="estado" role="alert">
        <TriangleAlert size={22} />
        <p>{estado.erro}</p>
        <button type="button" className="botao-texto" onClick={estado.recarregar}>
          Tentar de novo
        </button>
      </div>
    );
  }
  if (estado.dados === null) {
    return (
      <div className="esqueleto" aria-busy="true">
        <span className="sr-only">Carregando…</span>
        <div className="esqueleto-linha" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div className="esqueleto-bloco" aria-hidden="true" />
        <div className="esqueleto-linha" aria-hidden="true">
          <span />
          <span />
        </div>
      </div>
    );
  }
  return <>{children(estado.dados)}</>;
}
