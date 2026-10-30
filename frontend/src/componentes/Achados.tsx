import { CircleAlert, Info, TriangleAlert } from 'lucide-react';

import type { Achado } from '../api/tipos';

const ICONE = { alerta: TriangleAlert, atencao: CircleAlert, info: Info };

/** Padrões que o analítico detectou nos dados, escritos em frases (interpretação automática). */
export function Achados({ achados, subtitulo }: { achados: Achado[]; subtitulo: string }) {
  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>O que os dados mostram</h2>
          <p className="cartao-sub">{subtitulo}</p>
        </div>
      </div>
      <ul className="achados">
        {achados.map((achado) => {
          const Icone = ICONE[achado.gravidade];
          return (
            <li key={achado.titulo} className={achado.gravidade}>
              <Icone size={16} aria-hidden="true" />
              <div>
                <strong>{achado.titulo}</strong>
                <p>{achado.texto}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
