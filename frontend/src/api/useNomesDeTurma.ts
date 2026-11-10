import { useCallback, useRef, useState } from 'react';

import { api } from './cliente';
import type { Resposta } from './tipos';

/**
 * Devolve uma função que dá o nome de uma turma pelo id.
 *
 * As listas de turma da tela vêm limitadas (100). Uma turma fora delas não pode virar "Turma 199":
 * o nome que falta é buscado direto por `GET /academico/turmas/{id}`, uma vez por turma, e a tela
 * se atualiza quando ele chega. Enquanto isso (ou se a busca falhar), mostra "Turma {id}".
 */
export function useNomesDeTurma(conhecidas: { id: number; nome: string }[]) {
  const [buscadas, setBuscadas] = useState<Record<number, string>>({});
  const pedidas = useRef(new Set<number>());

  return useCallback(
    (id: number): string => {
      const nome = conhecidas.find((t) => t.id === id)?.nome ?? buscadas[id];
      if (nome) return nome;
      if (!pedidas.current.has(id)) {
        pedidas.current.add(id);
        // Fora da renderização: o React não deixa pedir dados nem mudar estado durante ela.
        queueMicrotask(() => {
          api<Resposta<{ nome: string }>>(`/academico/turmas/${id}`)
            .then((r) => setBuscadas((atual) => ({ ...atual, [id]: r.dados.nome })))
            .catch(() => pedidas.current.delete(id));
        });
      }
      return `Turma ${id}`;
    },
    [conhecidas, buscadas],
  );
}
