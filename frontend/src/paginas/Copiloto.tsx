import { Copy, SendHorizontal } from 'lucide-react';
import { type FormEvent, useEffect, useRef, useState } from 'react';

import { api } from '../api/cliente';
import type { Resposta, RespostaCopiloto } from '../api/tipos';

interface Mensagem {
  autor: 'usuario' | 'copiloto';
  texto: string;
  resposta?: RespostaCopiloto;
}

const SUGESTOES_INICIAIS = [
  'Quais alunos precisam de monitoria urgente?',
  'Gere um resumo do desempenho da turma para a reunião de colegiado',
  'Quem tirou abaixo de 5 e tem presença menor que 70%?',
  'Quantos alunos estão em risco?',
];

export function Copiloto() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([
    {
      autor: 'copiloto',
      texto:
        'Olá! Pergunte sobre monitoria, notas, frequência, a situação de um aluno ou peça um resumo. ' +
        'Eu respondo por regras, com os mesmos números do painel.',
    },
  ]);
  const [pergunta, setPergunta] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fim.current?.scrollIntoView?.({ block: 'end' });
  }, [mensagens]);

  async function perguntar(texto: string) {
    const limpa = texto.trim();
    if (limpa.length < 2 || enviando) return;
    setMensagens((m) => [...m, { autor: 'usuario', texto: limpa }]);
    setPergunta('');
    setEnviando(true);
    try {
      const r = await api<Resposta<RespostaCopiloto>>('/analitico/copiloto/perguntas', {
        method: 'POST',
        body: JSON.stringify({ pergunta: limpa }),
      });
      setMensagens((m) => [...m, { autor: 'copiloto', texto: r.dados.texto, resposta: r.dados }]);
    } catch (e) {
      setMensagens((m) => [...m, { autor: 'copiloto', texto: (e as Error).message }]);
    } finally {
      setEnviando(false);
    }
  }

  function enviar(e: FormEvent) {
    e.preventDefault();
    void perguntar(pergunta);
  }

  async function copiar(texto: string) {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      // Sem permissão da área de transferência: o texto continua visível na tela.
    }
  }

  const sugestoes = mensagens.at(-1)?.resposta?.sugestoes.length
    ? mensagens.at(-1)!.resposta!.sugestoes
    : SUGESTOES_INICIAIS;

  return (
    <section className="cartao copiloto">
      <div className="cartao-topo">
        <div>
          <h2>Copiloto</h2>
          <p className="cartao-sub">
            Consulta em linguagem natural, por regras e sem modelo de linguagem. Cada resposta cita o
            recorte usado.
          </p>
        </div>
      </div>

      <div className="conversa" role="log" aria-live="polite">
        {mensagens.map((m, i) => (
          <div key={i} className={`mensagem ${m.autor}`}>
            <p>{m.texto}</p>
            {m.resposta && m.resposta.recorte && m.autor === 'copiloto' && (
              <small className="cartao-sub">Recorte: {m.resposta.recorte}</small>
            )}
            {m.resposta?.itens.length ? (
              <ul className="lista-simples">
                {m.resposta.itens.map((item) => (
                  <li key={`${item.aluno_id}-${item.detalhe}`}>
                    <strong>{item.aluno_nome}</strong> <small className="cartao-sub">{item.matricula}</small>
                    <br />
                    {item.detalhe}
                  </li>
                ))}
                {m.resposta.total_itens > m.resposta.itens.length && (
                  <li className="cartao-sub">
                    … e mais {m.resposta.total_itens - m.resposta.itens.length}. Refine a pergunta.
                  </li>
                )}
              </ul>
            ) : null}
            {m.resposta?.secoes.map((s) => (
              <div key={s.titulo}>
                <h3 className="titulo-secao">{s.titulo}</h3>
                <ul className="lista-simples">
                  {s.linhas.map((linha) => (
                    <li key={linha}>{linha}</li>
                  ))}
                </ul>
              </div>
            ))}
            {m.resposta?.texto_completo && (
              <button type="button" className="botao-texto" onClick={() => copiar(m.resposta!.texto_completo!)}>
                <Copy size={14} aria-hidden="true" /> {copiado ? 'Copiado' : 'Copiar texto'}
              </button>
            )}
          </div>
        ))}
        {enviando && <p className="cartao-sub">Pensando…</p>}
        <div ref={fim} />
      </div>

      <div className="segmentos" role="group" aria-label="Sugestões de pergunta">
        {sugestoes.map((s) => (
          <button key={s} type="button" disabled={enviando} onClick={() => perguntar(s)}>
            {s}
          </button>
        ))}
      </div>

      <form className="envio" onSubmit={enviar}>
        <label className="sr-only" htmlFor="pergunta-copiloto">
          Sua pergunta
        </label>
        <input
          id="pergunta-copiloto"
          type="text"
          value={pergunta}
          maxLength={300}
          placeholder="Pergunte sobre a turma…"
          onChange={(e) => setPergunta(e.target.value)}
        />
        <button type="submit" className="botao-primario" disabled={enviando || pergunta.trim().length < 2}>
          <SendHorizontal size={16} aria-hidden="true" /> Enviar
        </button>
      </form>
    </section>
  );
}
