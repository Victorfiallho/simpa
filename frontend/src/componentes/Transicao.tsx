import { m } from 'motion/react';
import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

import { useEntradaDePagina } from '../movimento';

/** Cada tela nova entra com um leve deslocamento; os cartões dela entram em sequência (CSS). */
export function Transicao({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const entrada = useEntradaDePagina();
  return (
    <m.div key={pathname} className="transicao" {...entrada}>
      {children}
    </m.div>
  );
}
