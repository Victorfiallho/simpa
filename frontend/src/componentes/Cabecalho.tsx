import { CalendarDays, ChevronDown, UsersRound } from 'lucide-react';

import type { FiltroTurma } from '../dados/painel';

interface Props {
  titulo: string;
  periodo: string;
  turma: FiltroTurma;
  aoMudarTurma: (turma: FiltroTurma) => void;
}

export function Cabecalho({ titulo, periodo, turma, aoMudarTurma }: Props) {
  return (
    <header className="cabecalho">
      <h1>{titulo}</h1>
      <div className="filtros">
        <span className="aviso-demo">Dados de demonstração</span>
        <label className="filtro">
          <CalendarDays size={15} aria-hidden="true" />
          <span className="sr-only">Período letivo</span>
          <select value={periodo} onChange={() => undefined}>
            <option value={periodo}>{periodo}</option>
          </select>
          <ChevronDown size={14} className="seta" aria-hidden="true" />
        </label>
        <label className="filtro">
          <UsersRound size={15} aria-hidden="true" />
          <span className="sr-only">Turma</span>
          <select value={turma} onChange={(e) => aoMudarTurma(e.target.value as FiltroTurma)}>
            <option value="todas">Todas as turmas</option>
            <option value="A">IA · 2º período A</option>
            <option value="B">IA · 2º período B</option>
          </select>
          <ChevronDown size={14} className="seta" aria-hidden="true" />
        </label>
      </div>
    </header>
  );
}
