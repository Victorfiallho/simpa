import { X } from 'lucide-react';
import type { ReactNode } from 'react';

/** Painel lateral para formulários e detalhes. O fundo escurecido fecha ao clicar fora. */
export function Gaveta({
  titulo,
  subtitulo,
  aoFechar,
  children,
}: {
  titulo: string;
  subtitulo?: string;
  aoFechar: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="gaveta-fundo"
      role="dialog"
      aria-modal="true"
      aria-label={titulo}
      onClick={(e) => e.target === e.currentTarget && aoFechar()}
    >
      <div className="gaveta">
        <div className="gaveta-topo">
          <div>
            <h2>{titulo}</h2>
            {subtitulo && <p className="cartao-sub">{subtitulo}</p>}
          </div>
          <button type="button" className="botao-icone" onClick={aoFechar} aria-label="Fechar">
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
