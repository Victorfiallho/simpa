import { BellRing, ClipboardPen, X } from 'lucide-react';
import { type FormEvent, useState } from 'react';

import { api } from '../api/cliente';
import type {
  Alerta,
  EstadoAtendimento,
  ListaAlertas,
  NivelAlerta,
  Resposta,
  TipoAcompanhamento,
  TipoAlerta,
} from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';

const ROTULO_TIPO: Record<TipoAlerta, string> = {
  queda: 'Quebra de padrão',
  frequencia: 'Frequência no limite',
  abandono: 'Abandono silencioso',
};
const ROTULO_ESTADO: Record<EstadoAtendimento, string> = {
  pendente: 'Pendente',
  acomp: 'Em acompanhamento',
  encerrado: 'Encerrado',
};
const ROTULO_ACOMPANHAMENTO: Record<TipoAcompanhamento, string> = {
  contato: 'Contato realizado',
  orientacao: 'Orientação',
  monitoria: 'Encaminhamento para monitoria',
};
const TIPOS: TipoAlerta[] = ['queda', 'frequencia', 'abandono'];

/** A gravidade vira texto junto da cor, nunca só a cor (RNF12). */
function Gravidade({ nivel }: { nivel: NivelAlerta }) {
  const classe = nivel === 'alto' ? 'em_risco' : 'atencao';
  return (
    <span className={`selo ${classe}`}>
      <span className="ponto" aria-hidden="true" />
      {nivel === 'alto' ? 'Alta' : 'Atenção'}
    </span>
  );
}

const chave = (a: Alerta) => `${a.aluno_id}|${a.tipo}|${a.disciplina_id}`;
const hoje = () => new Date().toISOString().slice(0, 10);

export function Alertas({ turmaId, periodo }: { turmaId: number | null; periodo: string | null }) {
  const [tipo, setTipo] = useState<TipoAlerta | ''>('');
  const [apenasAltos, setApenasAltos] = useState(false);
  const [estado, setEstado] = useState<EstadoAtendimento | ''>('');
  const [acompanhar, setAcompanhar] = useState<Alerta | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const consulta = new URLSearchParams();
  if (turmaId) consulta.set('turma_id', String(turmaId));
  if (periodo) consulta.set('periodo_letivo', periodo);
  const lista = useDados(
    () => api<Resposta<ListaAlertas>>(`/analitico/alertas?${consulta}`).then((r) => r.dados),
    [consulta.toString()],
  );

  async function mudarEstado(alerta: Alerta, novo: EstadoAtendimento) {
    setErro(null);
    try {
      await api('/analitico/alertas/atendimento', {
        method: 'PUT',
        body: JSON.stringify({
          aluno_id: alerta.aluno_id,
          tipo: alerta.tipo,
          disciplina_id: alerta.disciplina_id,
          estado: novo,
        }),
      });
      lista.recarregar();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  return (
    <Conteudo estado={lista}>
      {({ resumo, alertas }) => {
        const visiveis = alertas.filter(
          (a) =>
            (!tipo || a.tipo === tipo) &&
            (!apenasAltos || a.nivel === 'alto') &&
            (!estado || a.estado === estado),
        );
        return (
          <div className="coluna">
            <section className="cartao">
              <div className="kpis">
                {resumo.map((r) => (
                  <div key={r.tipo} className="kpi">
                    <span className="kpi-rotulo">{ROTULO_TIPO[r.tipo]}</span>
                    <div className="kpi-valor num">{r.total}</div>
                    <div className="kpi-rodape">
                      {r.graves} com gravidade alta · {r.pendentes} pendente(s)
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="cartao">
              <div className="cartao-topo">
                <div>
                  <h2>Alertas ativos</h2>
                  <p className="cartao-sub">
                    {visiveis.length} de {alertas.length} alerta(s), do mais grave para o menos
                    grave. Os encerrados ficam por último.
                  </p>
                </div>
              </div>

              <div className="ferramentas">
                <div className="segmentos" role="group" aria-label="Filtrar por sinal">
                  <button type="button" aria-pressed={tipo === ''} onClick={() => setTipo('')}>
                    Todos <span className="contagem">{alertas.length}</span>
                  </button>
                  {TIPOS.map((t) => (
                    <button key={t} type="button" aria-pressed={tipo === t} onClick={() => setTipo(t)}>
                      {ROTULO_TIPO[t]}
                    </button>
                  ))}
                </div>
                <label className="campo campo-linha">
                  Situação
                  <select value={estado} onChange={(e) => setEstado(e.target.value as EstadoAtendimento | '')}>
                    <option value="">Todas</option>
                    {(Object.keys(ROTULO_ESTADO) as EstadoAtendimento[]).map((e) => (
                      <option key={e} value={e}>
                        {ROTULO_ESTADO[e]}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="campo campo-linha">
                  <input type="checkbox" checked={apenasAltos} onChange={(e) => setApenasAltos(e.target.checked)} />
                  Somente gravidade alta
                </label>
              </div>

              {erro && (
                <p className="erro-campo" role="alert">
                  {erro}
                </p>
              )}

              {visiveis.length === 0 ? (
                <p className="vazio">
                  <BellRing size={20} aria-hidden="true" /> Nenhum alerta neste recorte.
                </p>
              ) : (
                <div className="tabela-rolagem">
                  <table className="tabela">
                    <thead>
                      <tr>
                        <th>Aluno</th>
                        <th>Sinal</th>
                        <th>O que aconteceu</th>
                        <th>Gravidade</th>
                        <th>Atendimento</th>
                        <th>Ação sugerida</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visiveis.map((a) => (
                        <tr key={chave(a)} className={a.estado === 'encerrado' ? 'encerrado' : undefined}>
                          <td>
                            <strong>{a.aluno_nome}</strong>
                            <br />
                            <small className="cartao-sub">{a.matricula}</small>
                          </td>
                          <td>
                            <strong>{ROTULO_TIPO[a.tipo]}</strong>
                            <br />
                            <small className="cartao-sub">{a.disciplina_nome}</small>
                          </td>
                          <td>
                            {a.titulo}
                            <br />
                            <small className="cartao-sub">{a.detalhe}</small>
                          </td>
                          <td>
                            <Gravidade nivel={a.nivel} />
                          </td>
                          <td>
                            <select
                              value={a.estado}
                              aria-label={`Atendimento de ${a.aluno_nome}`}
                              onChange={(e) => mudarEstado(a, e.target.value as EstadoAtendimento)}
                            >
                              {(Object.keys(ROTULO_ESTADO) as EstadoAtendimento[]).map((e) => (
                                <option key={e} value={e}>
                                  {ROTULO_ESTADO[e]}
                                </option>
                              ))}
                            </select>
                            <br />
                            <small className="cartao-sub">{a.ultimo_contato}</small>
                          </td>
                          <td>
                            {a.acao_sugerida}
                            <br />
                            <button type="button" className="botao-texto" onClick={() => setAcompanhar(a)}>
                              <ClipboardPen size={14} aria-hidden="true" /> Registrar acompanhamento
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {acompanhar && (
              <FormularioAcompanhamento
                alerta={acompanhar}
                aoFechar={() => setAcompanhar(null)}
                aoSalvar={() => {
                  setAcompanhar(null);
                  lista.recarregar();
                }}
              />
            )}
          </div>
        );
      }}
    </Conteudo>
  );
}

function FormularioAcompanhamento({
  alerta,
  aoFechar,
  aoSalvar,
}: {
  alerta: Alerta;
  aoFechar: () => void;
  aoSalvar: () => void;
}) {
  const [tipo, setTipo] = useState<TipoAcompanhamento>('contato');
  const [data, setData] = useState(hoje());
  const [observacao, setObservacao] = useState('');
  const [revisao, setRevisao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      await api('/analitico/acompanhamentos', {
        method: 'POST',
        body: JSON.stringify({
          aluno_id: alerta.aluno_id,
          disciplina_id: alerta.disciplina_id || null,
          tipo,
          data,
          observacao,
          revisao: revisao || null,
        }),
      });
      aoSalvar();
    } catch (err) {
      setErro((err as Error).message);
      setEnviando(false);
    }
  }

  return (
    <div className="gaveta-fundo" role="dialog" aria-modal="true" aria-label="Registrar acompanhamento">
      <div className="gaveta">
        <div className="gaveta-topo">
          <div>
            <h2>Registrar acompanhamento</h2>
            <p className="cartao-sub">
              {alerta.aluno_nome} · {alerta.matricula}
            </p>
          </div>
          <button type="button" className="botao-icone" onClick={aoFechar} aria-label="Fechar">
            <X size={18} />
          </button>
        </div>
        <form className="coluna" onSubmit={enviar}>
          <label className="campo">
            Ação realizada
            <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoAcompanhamento)}>
              {(Object.keys(ROTULO_ACOMPANHAMENTO) as TipoAcompanhamento[]).map((t) => (
                <option key={t} value={t}>
                  {ROTULO_ACOMPANHAMENTO[t]}
                </option>
              ))}
            </select>
          </label>
          <label className="campo">
            Data
            <input type="date" value={data} max={hoje()} required onChange={(e) => setData(e.target.value)} />
          </label>
          <label className="campo">
            Observação curta
            <textarea
              value={observacao}
              minLength={3}
              maxLength={200}
              rows={3}
              required
              onChange={(e) => setObservacao(e.target.value)}
              placeholder="Ex.: Conversa realizada; encaminhado à monitoria."
            />
          </label>
          <label className="campo">
            Próxima revisão (opcional)
            <input type="date" value={revisao} min={data} onChange={(e) => setRevisao(e.target.value)} />
          </label>
          {erro && (
            <p className="erro-campo" role="alert">
              {erro}
            </p>
          )}
          <button type="submit" className="botao-primario" disabled={enviando}>
            {enviando ? 'Salvando…' : 'Registrar'}
          </button>
        </form>
      </div>
    </div>
  );
}
