import type { Situacao } from '../api/tipos';
import { ROTULO_SITUACAO } from '../dados/formato';

/** Situação sempre escrita junto da cor, nunca só a cor (RNF12). */
export function Selo({ situacao }: { situacao: Situacao }) {
  return (
    <span className={`selo ${situacao}`}>
      <span className="ponto" aria-hidden="true" />
      {ROTULO_SITUACAO[situacao]}
    </span>
  );
}
