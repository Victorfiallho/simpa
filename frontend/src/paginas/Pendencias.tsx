import { Inbox } from 'lucide-react';
import { useState } from 'react';

import { api } from '../api/cliente';
import type { EstadoApoio, Resposta, SolicitacaoDaCoordenacao } from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';
import { formatarDataHora } from '../dados/formato';

export const ROTULO_APOIO: Record<EstadoApoio, string> = {
  recebida: 'Recebida',
  atendimento: 'Em atendimento',
  concluida: 'Concluída',
};
const ESTADOS = Object.keys(ROTULO_APOIO) as EstadoApoio[];

/** Pedidos de apoio enviados pelos alunos, para a coordenação atender (RF07). */
export function Pendencias() {
  const [filtro, setFiltro] = useState<EstadoApoio | ''>('');
  const [erro, setErro] = useState<string | null>(null);
  const lista = useDados(
    () =>
      api<Resposta<SolicitacaoDaCoordenacao[]>>(`/analitico/apoio${filtro ? `?estado=${filtro}` : ''}`).then(
        (r) => r.dados,
      ),
    [filtro],
  );

  async function mudar(id: number, estado: EstadoApoio) {
    setErro(null);
    try {
      await api(`/analitico/apoio/${id}/estado`, { method: 'PUT', body: JSON.stringify({ estado }) });
      lista.recarregar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Pedidos de apoio</h2>
          <p className="cartao-sub">Do mais recente para o mais antigo.</p>
        </div>
      </div>
      <div className="ferramentas">
        <div className="segmentos" role="group" aria-label="Filtrar por situação">
          <button type="button" aria-pressed={filtro === ''} onClick={() => setFiltro('')}>
            Todos
          </button>
          {ESTADOS.map((e) => (
            <button key={e} type="button" aria-pressed={filtro === e} onClick={() => setFiltro(e)}>
              {ROTULO_APOIO[e]}
            </button>
          ))}
        </div>
      </div>
      {erro && (
        <p className="erro-campo" role="alert">
          {erro}
        </p>
      )}
      <Conteudo estado={lista}>
        {(pedidos) =>
          pedidos.length === 0 ? (
            <p className="vazio">
              <Inbox size={20} aria-hidden="true" /> Nenhum pedido neste recorte.
            </p>
          ) : (
            <div className="tabela-rolagem">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Aluno</th>
                    <th>Pedido</th>
                    <th>Enviado em</th>
                    <th>Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {pedidos.map((p) => (
                    <tr key={p.id} className={p.estado === 'concluida' ? 'encerrado' : undefined}>
                      <td>
                        <strong>{p.aluno_nome ?? `Aluno ${p.aluno_id}`}</strong>
                        <br />
                        <small className="cartao-sub">{p.matricula}</small>
                      </td>
                      <td>
                        <strong>{p.motivo}</strong> · {p.disciplina_nome ?? 'Geral'}
                        <br />
                        <small className="cartao-sub">{p.texto}</small>
                      </td>
                      <td>{formatarDataHora(p.criada_em)}</td>
                      <td>
                        <select
                          value={p.estado}
                          aria-label={`Situação do pedido de ${p.aluno_nome ?? p.aluno_id}`}
                          onChange={(e) => mudar(p.id, e.target.value as EstadoApoio)}
                        >
                          {ESTADOS.map((e) => (
                            <option key={e} value={e}>
                              {ROTULO_APOIO[e]}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
      </Conteudo>
    </section>
  );
}
