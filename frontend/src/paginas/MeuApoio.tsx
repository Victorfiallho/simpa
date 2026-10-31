import { type FormEvent, useState } from 'react';

import { api } from '../api/cliente';
import type { Resposta, Solicitacao } from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';
import { formatarDataHora } from '../dados/formato';
import { ROTULO_APOIO } from './Pendencias';

const MOTIVOS = ['Dificuldade no conteúdo', 'Faltas', 'Questão pessoal', 'Outro'];

/** Pedido de apoio à coordenação e acompanhamento dos pedidos já enviados (RF07). */
export function MeuApoio() {
  const pedidos = useDados(
    () => api<Resposta<Solicitacao[]>>('/analitico/meu/apoio').then((r) => r.dados),
    [],
  );
  const [motivo, setMotivo] = useState(MOTIVOS[0]);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      await api('/analitico/meu/apoio', {
        method: 'POST',
        body: JSON.stringify({ disciplina_id: null, motivo, texto }),
      });
      setTexto('');
      pedidos.recarregar();
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="coluna">
      <section className="cartao">
        <div className="cartao-topo">
          <div>
            <h2>Pedir apoio</h2>
            <p className="cartao-sub">A coordenação recebe o pedido e acompanha até concluir.</p>
          </div>
        </div>
        <form className="coluna" onSubmit={enviar}>
          <label className="campo">
            Motivo
            <select value={motivo} onChange={(e) => setMotivo(e.target.value)}>
              {MOTIVOS.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </label>
          <label className="campo">
            Conte o que está acontecendo
            <textarea
              value={texto}
              minLength={3}
              maxLength={200}
              rows={3}
              required
              onChange={(e) => setTexto(e.target.value)}
            />
          </label>
          {erro && (
            <p className="erro-campo" role="alert">
              {erro}
            </p>
          )}
          <button type="submit" className="botao-primario" disabled={enviando}>
            {enviando ? 'Enviando…' : 'Enviar pedido'}
          </button>
        </form>
      </section>

      <section className="cartao">
        <div className="cartao-topo">
          <h2>Meus pedidos</h2>
        </div>
        <Conteudo estado={pedidos}>
          {(lista) =>
            lista.length === 0 ? (
              <p className="vazio">Você ainda não enviou nenhum pedido.</p>
            ) : (
              <ul className="coluna">
                {lista.map((p) => (
                  <li key={p.id}>
                    <strong>{p.motivo}</strong> · {ROTULO_APOIO[p.estado]}
                    <br />
                    <small className="cartao-sub">
                      {p.texto} · enviado em {formatarDataHora(p.criada_em)}
                    </small>
                  </li>
                ))}
              </ul>
            )
          }
        </Conteudo>
      </section>
    </div>
  );
}
