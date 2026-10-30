import { useState } from 'react';
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

import { api } from '../api/cliente';
import type { Predicao as DadosPredicao, Resposta } from '../api/tipos';
import { useDados } from '../api/useDados';
import { COR_SITUACAO, formatarNota, formatarPercentual } from '../dados/formato';
import { EIXO, GRADE } from '../paginas/VisaoGeral';
import { Conteudo } from './Conteudo';
import { Selo } from './Selo';

function formatarNumero(valor: number, casas = 2): string {
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function Modelo({ dados }: { dados: DadosPredicao }) {
  const modelo = dados.modelo!;
  const pontos = dados.previsoes
    .filter((p) => p.nota_n2_real !== null)
    .map((p) => ({ ...p, x: Number(p.nota_n2_real), y: Number(p.nota_n2_prevista) }));

  return (
    <div className="graficos">
      <section className="cartao">
        <div className="cartao-topo">
          <div>
            <h2>Modelo de regressão linear</h2>
            <p className="cartao-sub">
              Mínimos quadrados em forma matricial: β = (XᵀX)⁻¹Xᵀy, com {modelo.n} inscrições
            </p>
          </div>
        </div>
        <p className="equacao num">{modelo.equacao}</p>
        <div className="estatisticas estatisticas-3">
          <div>
            <span>R²</span>
            <strong className="num">{formatarNumero(modelo.r2)}</strong>
            <small>variação da N2 explicada</small>
          </div>
          <div>
            <span>Erro médio</span>
            <strong className="num">{formatarNumero(modelo.erro_validacao)}</strong>
            <small>ponto, deixando cada um de fora</small>
          </div>
          <div>
            <span>Acerto do risco</span>
            <strong className="num">{formatarNumero(modelo.acerto_risco, 0)}%</strong>
            <small>situação final prevista corretamente</small>
          </div>
        </div>
        <ul className="lista-simples">
          {modelo.interpretacao.map((frase) => (
            <li key={frase}>{frase}</li>
          ))}
        </ul>
      </section>

      <section className="cartao">
        <div className="cartao-topo">
          <div>
            <h2>Previsto × real</h2>
            <p className="cartao-sub">Cada ponto é uma inscrição; quanto mais perto da diagonal, melhor</p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid stroke={GRADE} strokeDasharray="3 4" />
            <XAxis type="number" dataKey="x" name="N2 real" domain={[0, 10]} ticks={[0, 2, 4, 6, 8, 10]} tick={EIXO} tickLine={false} axisLine={false} />
            <YAxis type="number" dataKey="y" name="N2 prevista" domain={[0, 10]} ticks={[0, 2, 4, 6, 8, 10]} tick={EIXO} tickLine={false} axisLine={false} />
            <ZAxis range={[36, 36]} />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 10, y: 10 }]} stroke="#c9c4b6" strokeDasharray="4 4" />
            <Tooltip
              content={({ active, payload }) => {
                const p = payload?.[0]?.payload as (typeof pontos)[number] | undefined;
                if (!active || !p) return null;
                return (
                  <div className="dica">
                    <strong>{p.aluno}</strong>
                    <div>{p.disciplina}</div>
                    <div className="num">
                      N2 real {formatarNota(p.nota_n2_real)} · prevista {formatarNota(p.nota_n2_prevista)}
                    </div>
                  </div>
                );
              }}
            />
            <Scatter data={pontos} fill="#2c2c2c" fillOpacity={0.7} />
          </ScatterChart>
        </ResponsiveContainer>
        <p className="legenda">Eixo horizontal: N2 lançada. Eixo vertical: N2 prevista pelo modelo.</p>
      </section>
    </div>
  );
}

function Projecoes({ dados }: { dados: DadosPredicao }) {
  const [todos, setTodos] = useState(false);
  const emRisco = dados.previsoes.filter((p) => p.risco_projetado);
  const linhas = todos ? dados.previsoes : emRisco;

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Risco projetado</h2>
          <p className="cartao-sub">
            Média final estimada a partir da N1 e da frequência da N1. {emRisco.length} inscrições
            projetadas em risco.
          </p>
        </div>
        <button type="button" className="botao-texto" onClick={() => setTodos((v) => !v)}>
          {todos ? 'Só as em risco' : 'Ver todas'}
        </button>
      </div>
      <div className="tabela-rolagem">
        <table className="tabela">
          <thead>
            <tr>
              <th>Aluno</th>
              <th>Disciplina</th>
              <th className="direita">N1</th>
              <th className="direita">Freq. N1</th>
              <th className="direita">N2 prevista</th>
              <th className="direita">Média projetada</th>
              <th>Situação atual</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((p) => (
              <tr key={p.inscricao_id}>
                <td>
                  <strong>{p.aluno}</strong>
                  <small className="detalhe num">{p.matricula}</small>
                </td>
                <td>{p.disciplina}</td>
                <td className="direita num">{formatarNota(p.nota_n1)}</td>
                <td className="direita num">{formatarPercentual(p.frequencia_n1)}</td>
                <td className="direita num">{formatarNota(p.nota_n2_prevista)}</td>
                <td className="direita num">
                  <span style={{ color: p.risco_projetado ? COR_SITUACAO.em_risco : undefined, fontWeight: 600 }}>
                    {formatarNota(p.media_projetada)}
                  </span>
                </td>
                <td>
                  <Selo situacao={p.situacao_atual} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {linhas.length === 0 && <p className="vazio">Nenhuma inscrição projetada em risco.</p>}
      </div>
      <ul className="lista-simples limites">
        {dados.limites.map((limite) => (
          <li key={limite}>{limite}</li>
        ))}
      </ul>
    </section>
  );
}

export function Predicao({ turmaId, periodo }: { turmaId: number | null; periodo: string | null }) {
  const consulta = new URLSearchParams();
  if (turmaId) consulta.set('turma_id', String(turmaId));
  if (periodo) consulta.set('periodo_letivo', periodo);
  const predicao = useDados(
    () => api<Resposta<DadosPredicao>>(`/analitico/predicao?${consulta}`).then((r) => r.dados),
    [consulta.toString()],
  );

  return (
    <div className="coluna">
      <div className="titulo-secao">
        <h2>Predição</h2>
        <p className="cartao-sub">
          Regressão linear múltipla: estima a N2 a partir da nota e da frequência da N1
        </p>
      </div>
      <Conteudo estado={predicao}>
        {(dados) =>
          dados.modelo ? (
            <>
              <Modelo dados={dados} />
              <Projecoes dados={dados} />
            </>
          ) : (
            <p className="vazio">{dados.observacao}</p>
          )
        }
      </Conteudo>
    </div>
  );
}
