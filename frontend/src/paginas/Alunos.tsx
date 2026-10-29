import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';

import type { AlunoPainel, Painel, Situacao } from '../api/tipos';
import { DetalheAluno } from '../componentes/DetalheAluno';
import { Selo } from '../componentes/Selo';
import {
  formatarNota,
  formatarPercentual,
  iniciais,
  ORDEM_SITUACAO,
  ROTULO_SITUACAO,
} from '../dados/formato';

type FiltroSituacao = 'todos' | Situacao;

function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
}

export function Alunos({ painel }: { painel: Painel }) {
  const [busca, setBusca] = useState('');
  const [situacao, setSituacao] = useState<FiltroSituacao>('todos');
  const [selecionado, setSelecionado] = useState<AlunoPainel | null>(null);

  const alunos = useMemo(() => {
    const termo = normalizar(busca.trim());
    return painel.alunos
      .filter((a) => situacao === 'todos' || a.situacao === situacao)
      .filter((a) => !termo || normalizar(`${a.nome} ${a.matricula}`).includes(termo))
      .sort(
        (a, b) =>
          ORDEM_SITUACAO.indexOf(a.situacao) - ORDEM_SITUACAO.indexOf(b.situacao) ||
          a.nome.localeCompare(b.nome, 'pt-BR'),
      );
  }, [painel, busca, situacao]);

  const opcoes: { valor: FiltroSituacao; rotulo: string; total: number }[] = [
    { valor: 'todos', rotulo: 'Todos', total: painel.total_alunos },
    ...ORDEM_SITUACAO.map((s) => ({ valor: s, rotulo: ROTULO_SITUACAO[s], total: painel.contagem[s] })),
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
              aria-pressed={situacao === o.valor}
              onClick={() => setSituacao(o.valor)}
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
              const emRisco = aluno.inscricoes.filter((i) => i.situacao === 'em_risco');
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
                  <td>{aluno.turma_nome}</td>
                  <td className="direita num">{formatarNota(aluno.media)}</td>
                  <td className="direita num">{formatarPercentual(aluno.frequencia)}</td>
                  <td>{emRisco.length ? emRisco.map((i) => i.disciplina_nome).join(', ') : '—'}</td>
                  <td>
                    <Selo situacao={aluno.situacao} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {alunos.length === 0 && <p className="vazio">Nenhum aluno encontrado com esses filtros.</p>}
      </div>

      {selecionado && <DetalheAluno aluno={selecionado} aoFechar={() => setSelecionado(null)} />}
    </section>
  );
}
