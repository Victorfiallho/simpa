import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';

import { DetalheAluno } from '../componentes/DetalheAluno';
import { Selo } from '../componentes/Selo';
import type { AlunoConsolidado } from '../dados/calculos';
import {
  formatarNota,
  formatarPercentual,
  iniciais,
  ORDEM_STATUS,
  ROTULO_STATUS,
} from '../dados/formato';
import type { Painel } from '../dados/painel';
import type { Status } from '../dados/tipos';

type FiltroStatus = 'todos' | Status;

function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

export function Alunos({ painel }: { painel: Painel }) {
  const [busca, setBusca] = useState('');
  const [status, setStatus] = useState<FiltroStatus>('todos');
  const [selecionado, setSelecionado] = useState<AlunoConsolidado | null>(null);

  const alunos = useMemo(() => {
    const termo = normalizar(busca.trim());
    return painel.alunos
      .filter((a) => status === 'todos' || a.status === status)
      .filter((a) => !termo || normalizar(`${a.nome} ${a.matricula}`).includes(termo))
      .sort(
        (a, b) =>
          ORDEM_STATUS.indexOf(a.status) - ORDEM_STATUS.indexOf(b.status) ||
          a.nome.localeCompare(b.nome, 'pt-BR'),
      );
  }, [painel, busca, status]);

  const opcoes: { valor: FiltroStatus; rotulo: string; total: number }[] = [
    { valor: 'todos', rotulo: 'Todos', total: painel.alunos.length },
    ...ORDEM_STATUS.map((s) => ({ valor: s, rotulo: ROTULO_STATUS[s], total: painel.contagem[s] })),
  ];

  return (
    <section className="cartao">
      <div className="ferramentas">
        <label className="busca">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Buscar aluno</span>
          <input
            type="search"
            placeholder="Buscar por nome ou matrícula"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </label>
        <div className="segmentos" role="group" aria-label="Filtrar por situação">
          {opcoes.map((o) => (
            <button
              key={o.valor}
              type="button"
              aria-pressed={status === o.valor}
              onClick={() => setStatus(o.valor)}
            >
              {o.rotulo} <span className="contagem num">{o.total}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="tabela-rolagem">
        <table className="tabela">
          <thead>
            <tr>
              <th>Aluno</th>
              <th>Turma</th>
              <th className="direita">Média</th>
              <th className="direita">Frequência</th>
              <th>Disciplinas em risco</th>
              <th>Situação</th>
            </tr>
          </thead>
          <tbody>
            {alunos.map((aluno) => {
              const emRisco = aluno.resumos.filter((r) => r.status === 'em_risco');
              return (
                <tr key={aluno.id}>
                  <td>
                    <button type="button" className="pessoa" onClick={() => setSelecionado(aluno)}>
                      <span className="avatar">{iniciais(aluno.nome)}</span>
                      <span>
                        <strong>{aluno.nome}</strong>
                        <small className="num">{aluno.matricula}</small>
                      </span>
                    </button>
                  </td>
                  <td>Turma {aluno.turma}</td>
                  <td className="direita num">{formatarNota(aluno.media)}</td>
                  <td className="direita num">{formatarPercentual(aluno.frequencia)}</td>
                  <td>{emRisco.length ? emRisco.map((r) => r.disciplina.sigla).join(', ') : '—'}</td>
                  <td>
                    <Selo status={aluno.status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {alunos.length === 0 && <p className="vazio">Nenhum aluno encontrado com esses filtros.</p>}
      </div>

      {selecionado && (
        <DetalheAluno
          aluno={selecionado}
          periodo={painel.periodoLetivo}
          aoFechar={() => setSelecionado(null)}
        />
      )}
    </section>
  );
}
