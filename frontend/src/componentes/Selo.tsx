import { ROTULO_STATUS } from '../dados/formato';
import type { Status } from '../dados/tipos';

/** Status sempre escrito junto da cor, nunca só a cor (RNF12). */
export function Selo({ status }: { status: Status }) {
  return (
    <span className={`selo ${status}`}>
      <span className="ponto" aria-hidden="true" />
      {ROTULO_STATUS[status]}
    </span>
  );
}
