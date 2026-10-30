import { Search } from 'lucide-react';
import { useState } from 'react';

import { api } from '../api/cliente';
import type { RegistroAuditoria, RespostaPaginada } from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';
import { formatarDataHora } from '../dados/formato';

const LIMITE = 25;
const CLASSES = [
  { valor: '', rotulo: 'Todos os status' },
  { valor: '2', rotulo: 'Sucesso (2xx)' },
  { valor: '4', rotulo: 'Erro do cliente (4xx)' },
  { valor: '5', rotulo: 'Erro do servidor (5xx)' },
];

/** Status sempre com texto e cor juntos (RNF12). */
function classeDoStatus(status: number): string {
  if (status >= 500) return 'em_risco';
  if (status >= 400) return 'atencao';
  return 'sem_risco';
}

export function Auditoria() {
  const [classe, setClasse] = useState('');
  const [metodo, setMetodo] = useState('');
  const [busca, setBusca] = useState('');
  const [pagina, setPagina] = useState(1);

  const consulta = new URLSearchParams({
    pagina: String(pagina),
    limite: String(LIMITE),
    ordenar_por: 'timestamp',
    ordem: 'desc',
  });
  if (classe) consulta.set('classe_status', classe);
  if (metodo) consulta.set('metodo_http', metodo);
  if (busca.trim().length >= 2) consulta.set('busca', busca.trim());

  const registros = useDados(
    () => api<RespostaPaginada<RegistroAuditoria>>(`/auth/auditoria?${consulta}`),
    [consulta.toString()],
  );

  function filtrar(mudar: () => void) {
    mudar();
    setPagina(1);
  }

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Trilha de auditoria</h2>
          <p className="cartao-sub">
            Cada requisição registra quem fez, em qual rota, com qual resultado e em quanto tempo. Corpo,
            senha, token e CPF nunca são gravados.
          </p>
        </div>
      </div>

      <div className="ferramentas">
        <label className="busca">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Buscar por rota ou correlation id</span>
          <input
            type="search"
            value={busca}
            placeholder="Rota ou correlation id"
            onChange={(e) => filtrar(() => setBusca(e.target.value))}
          />
        </label>
        <label className="campo campo-linha">
          Status
          <select value={classe} onChange={(e) => filtrar(() => setClasse(e.target.value))}>
            {CLASSES.map((c) => (
              <option key={c.valor} value={c.valor}>
                {c.rotulo}
              </option>
            ))}
          </select>
        </label>
        <label className="campo campo-linha">
          Método
          <select value={metodo} onChange={(e) => filtrar(() => setMetodo(e.target.value))}>
            <option value="">Todos</option>
            {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </label>
      </div>

      <Conteudo estado={registros}>
        {(r) => {
          const paginas = Math.max(1, Math.ceil(r.total_registros / r.limite));
          return (
            <>
              {r.dados.length === 0 ? (
                <p className="vazio">Nenhum registro com esses filtros.</p>
              ) : (
                <div className="tabela-rolagem">
                  <table className="tabela">
                    <thead>
                      <tr>
                        <th>Data e hora</th>
                        <th>Usuário</th>
                        <th>Requisição</th>
                        <th>Status</th>
                        <th className="direita">Tempo</th>
                        <th>IP</th>
                        <th>Correlation id</th>
                      </tr>
                    </thead>
                    <tbody>
                      {r.dados.map((l) => (
                        <tr key={l.id}>
                          <td>{formatarDataHora(l.timestamp)}</td>
                          <td>{l.usuario_id === null ? <span className="cartao-sub">anônimo</span> : `#${l.usuario_id}`}</td>
                          <td>
                            <strong>{l.metodo_http}</strong> {l.rota}
                          </td>
                          <td>
                            <span className={`selo ${classeDoStatus(l.status_http)}`}>
                              <span className="ponto" aria-hidden="true" />
                              {l.status_http}
                            </span>
                          </td>
                          <td className="direita num">{l.tempo_resposta_ms} ms</td>
                          <td className="num">{l.ip_origem}</td>
                          <td>
                            <code>{l.correlation_id}</code>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="ferramentas" style={{ marginTop: 16, marginBottom: 0 }}>
                <p className="cartao-sub num">
                  {r.total_registros} registro(s) · página {r.pagina} de {paginas}
                </p>
                <div className="segmentos">
                  <button type="button" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>
                    Anterior
                  </button>
                  <button type="button" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)}>
                    Próxima
                  </button>
                </div>
              </div>
            </>
          );
        }}
      </Conteudo>
    </section>
  );
}
