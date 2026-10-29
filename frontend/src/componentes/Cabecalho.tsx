import { CalendarDays, ChevronDown, UsersRound } from 'lucide-react';

import type { Turma } from '../api/tipos';

export interface Filtros {
  periodo: string | null;
  turmaId: number | null;
}

interface Props {
  titulo: string;
  turmas: Turma[];
  filtros: Filtros;
  aoMudar: (filtros: Filtros) => void;
}

export function Cabecalho({ titulo, turmas, filtros, aoMudar }: Props) {
  const periodos = [...new Set(turmas.map((t) => t.periodo_letivo))].sort().reverse();
  const turmasDoPeriodo = turmas.filter((t) => !filtros.periodo || t.periodo_letivo === filtros.periodo);

  return (
    <header className="cabecalho">
      <h1>{titulo}</h1>
      <div className="filtros">
        <label className="filtro">
          <CalendarDays size={15} aria-hidden="true" />
          <span className="sr-only">Período letivo</span>
          <select
            value={filtros.periodo ?? ''}
            onChange={(e) => aoMudar({ periodo: e.target.value || null, turmaId: null })}
          >
            <option value="">Todos os períodos</option>
            {periodos.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="seta" aria-hidden="true" />
        </label>
        <label className="filtro">
          <UsersRound size={15} aria-hidden="true" />
          <span className="sr-only">Turma</span>
          <select
            value={filtros.turmaId ?? ''}
            onChange={(e) =>
              aoMudar({ ...filtros, turmaId: e.target.value ? Number(e.target.value) : null })
            }
          >
            <option value="">Todas as turmas</option>
            {turmasDoPeriodo.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="seta" aria-hidden="true" />
        </label>
      </div>
    </header>
  );
}
