import { X } from 'lucide-react';
import { useEffect, useRef } from 'react';

import { api } from '../api/cliente';
import type { AlunoPainel, Resposta, ResultadoRisco, Situacao } from '../api/tipos';
import { useDados } from '../api/useDados';
import {
  COR_SITUACAO,
  formatarDataHora,
  formatarNota,
  formatarPercentual,
  ROTULO_SITUACAO,
} from '../dados/formato';
import { Selo } from './Selo';

function situacaoDe(r: ResultadoRisco): Situacao {
  return r.status === 'sem_risco' && r.atencao ? 'atencao' : (r.status as Situacao);
}

/** Transições de risco de cada disciplina, gravadas pelo analítico (D11). */
function Historico({ aluno }: { aluno: AlunoPainel }) {
  const historico = useDados(
    () =>
      Promise.all(
        aluno.inscricoes.map((i) =>
          api<Resposta<ResultadoRisco[]>>(`/analitico/riscos/inscricoes/${i.inscricao_id}/historico`).then(
            (r) => r.dados.map((linha) => ({ ...linha, disciplina: i.disciplina_nome })),
          ),
        ),
      ).then((listas) => listas.flat().sort((a, b) => b.calculado_em.localeCompare(a.calculado_em))),
    [aluno.id],
  );

  if (historico.erro) return <p className="cartao-sub">{historico.erro}</p>;
  if (!historico.dados) return <p className="cartao-sub">Carregando histórico…</p>;
  if (historico.dados.length === 0) return <p className="cartao-sub">Nenhuma mudança registrada.</p>;

  return (
    <ol className="historico">
      {historico.dados.map((linha) => (
        <li key={linha.id}>
          <span className="ponto" style={{ color: COR_SITUACAO[situacaoDe(linha)] }} />
          <div>
            <strong>
              {linha.disciplina}: {ROTULO_SITUACAO[situacaoDe(linha)]}
            </strong>
            <small className="num">
              {formatarDataHora(linha.calculado_em)} · média {formatarNota(linha.media_final)} ·
              frequência {formatarPercentual(linha.frequencia_final)}
            </small>
          </div>
        </li>
      ))}
    </ol>
  );
}

interface Props {
  aluno: AlunoPainel;
  aoFechar: () => void;
}

export function DetalheAluno({ aluno, aoFechar }: Props) {
  const fechar = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    fechar.current?.focus();
    const aoTeclar = (e: KeyboardEvent) => e.key === 'Escape' && aoFechar();
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [aoFechar]);

  return (
    <div className="gaveta-fundo" onClick={aoFechar}>
      <aside
        className="gaveta"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-aluno"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="gaveta-topo">
          <div>
            <p className="cartao-sub num">
              Matrícula {aluno.matricula} · {aluno.turma_nome}
            </p>
            <h2 id="titulo-aluno">{aluno.nome}</h2>
          </div>
          <button ref={fechar} type="button" className="botao-icone" onClick={aoFechar}>
            <X size={16} />
            <span className="sr-only">Fechar</span>
          </button>
        </div>

        <div className="resumo-aluno">
          <div className="cartao">
            <span>Média</span>
            <strong className="num">{formatarNota(aluno.media)}</strong>
          </div>
          <div className="cartao">
            <span>Frequência</span>
            <strong className="num">{formatarPercentual(aluno.frequencia)}</strong>
          </div>
          <div className="cartao">
            <span>Situação</span>
            <strong>
              <Selo situacao={aluno.situacao} />
            </strong>
          </div>
        </div>

        <section className="cartao">
          <h2>Disciplinas</h2>
          <div className="tabela-rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Disciplina</th>
                  <th className="direita">N1</th>
                  <th className="direita">N2</th>
                  <th className="direita">Média</th>
                  <th className="direita">Frequência</th>
                  <th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {aluno.inscricoes.map((i) => (
                  <tr key={i.inscricao_id}>
                    <td>{i.disciplina_nome}</td>
                    <td className="direita num">{formatarNota(i.nota_n1)}</td>
                    <td className="direita num">{formatarNota(i.nota_n2)}</td>
                    <td className="direita num">{formatarNota(i.media)}</td>
                    <td className="direita num">
                      {formatarPercentual(i.frequencia)}
                      {i.aulas > 0 && (
                        <small className="detalhe">
                          {i.faltas} faltas em {i.aulas} aulas
                        </small>
                      )}
                    </td>
                    <td>
                      <Selo situacao={i.situacao} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="cartao-sub" style={{ marginTop: 10 }}>
            Média ponderada pelos pesos das avaliações, arredondada para 2 casas antes de classificar.
          </p>
        </section>

        <div className="motivos">
          {aluno.inscricoes.map((i) => (
            <div className="motivo" key={i.inscricao_id}>
              <span className="ponto" style={{ color: COR_SITUACAO[i.situacao] }} />
              <span>{i.justificativa}</span>
            </div>
          ))}
        </div>

        {aluno.recomendacoes.length > 0 && (
          <section className="cartao" style={{ marginTop: 16 }}>
            <h2>Recomendações</h2>
            <p className="cartao-sub">Sugestões de acompanhamento, da mais para a menos urgente</p>
            <ul className="recomendacoes">
              {aluno.recomendacoes.map((r) => (
                <li key={r.acao}>
                  <span className={`prioridade ${r.prioridade}`}>
                    {r.prioridade === 'alta' ? 'Alta' : r.prioridade === 'media' ? 'Média' : 'Baixa'}
                  </span>
                  <div>
                    <strong>{r.acao}</strong>
                    <small>{r.motivo}</small>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="cartao" style={{ marginTop: 16 }}>
          <h2>Histórico de risco</h2>
          <p className="cartao-sub">Cada mudança de situação, da mais recente para a mais antiga</p>
          <Historico aluno={aluno} />
        </section>
      </aside>
    </div>
  );
}
