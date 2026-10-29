import { createContext, type ReactNode, useContext, useEffect, useState } from 'react';

import { entrar as entrarNaApi, lerSessao, quandoExpirar, type Sessao, sair as sairDaApi } from './api/cliente';
import type { Usuario } from './api/tipos';

interface ContextoSessao {
  usuario: Usuario | null;
  expirou: boolean;
  entrar: (email: string, senha: string) => Promise<void>;
  sair: () => void;
}

const Contexto = createContext<ContextoSessao | null>(null);

export function ProvedorDeSessao({ children }: { children: ReactNode }) {
  const [sessao, setSessao] = useState<Sessao | null>(lerSessao);
  const [expirou, setExpirou] = useState(false);

  useEffect(() => {
    quandoExpirar(() => {
      setSessao(null);
      setExpirou(true);
    });
  }, []);

  const valor: ContextoSessao = {
    usuario: sessao?.usuario ?? null,
    expirou,
    entrar: async (email, senha) => {
      setSessao(await entrarNaApi(email, senha));
      setExpirou(false);
    },
    sair: () => {
      sairDaApi();
      setSessao(null);
    },
  };

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao(): ContextoSessao {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error('useSessao fora do ProvedorDeSessao');
  return contexto;
}
