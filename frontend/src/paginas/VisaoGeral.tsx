import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
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

import type { Painel, Situacao } from '../api/tipos';
import { Anel } from '../componentes/Anel';
import { Dica } from '../componentes/Dica';
import { Selo } from '../componentes/Selo';
import {
  COR_SITUACAO,
  formatarNota,
  formatarPercentual,
  iniciais,
  numero,
  ORDEM_SITUACAO,
  ROTULO_SITUACAO,
} from '../dados/formato';

export const EIXO = { fontSize: 11, fill: '#8b887f' };
export const GRADE = '#e2ddd0';
const SITUACOES_DO_GRAFICO: Situacao[] = ['sem_risco', 'atencao', 'indeterminado', 'em_risco'];

function Variacao({ atual, anterior, sufixo }: { atual: string | null; anterior: string | null; sufixo: string }) {
  if (atual === null || anterior === null) return null;
  const diferenca = Number(atual) - Number(anterior);
  const sobe = diferenca >= 0;
  return (
    <div className="kpi-rodape">
      <span className={`variacao ${sobe ? 'sobe' : 'desce'}`}>
        {sobe ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
      </span>
      <span className="num">
        {sobe ? '+' : '−'}
        {formatarNota(Math.abs(diferenca))}
      </span>
      {sufixo}
    </div>
  );
}

function Indicadores({ painel }: { painel: Painel }) {
  return (
    <section className="cartao kpis" aria-label="Indicadores gerais">
      <div className="kpi">
        <p className="kpi-rotulo">Alunos acompanhados</p>
        <p className="kpi-valor num">{painel.total_alunos}</p>
        <div className="kpi-rodape">
          {painel.total_inscricoes} inscrições
          {painel.inscricoes_sem_dados > 0 && `, ${painel.inscricoes_sem_dados} sem dados`}
        </div>
      </div>
      <div className="kpi">
        <p className="kpi-rotulo">Média geral</p>
        <p className="kpi-valor num">
          {formatarNota(painel.media_geral)}
          <small>/ 10</small>
        </p>
        <Variacao atual={painel.media_geral} anterior={painel.media_n1} sufixo="em relação à N1" />
      </div>
      <div className="kpi">
        <p className="kpi-rotulo">Frequência média</p>
        <p className="kpi-valor num">
          {formatarNota(painel.frequencia_geral)}
          <small>%</small>
        </p>
        <Variacao
          atual={painel.frequencia_geral}
          anterior={painel.frequencia_n1}
          sufixo="p.p. em relação à N1"
        />
      </div>
    </section>
  );
}

export function DistribuicaoMedias({ histograma }: { histograma: Painel['histograma'] }) {
  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Distribuição das médias</h2>
          <p className="cartao-sub">Inscrições por faixa de média final (0 a 10)</p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={histograma} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
          <CartesianGrid vertical={false} stroke={GRADE} strokeDasharray="3 4" />
          <XAxis dataKey="faixa" tick={EIXO} tickLine={false} axisLine={false} interval={0} />
          <YAxis allowDecimals={false} tick={EIXO} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: 'rgb(0 0 0 / 0.04)' }} content={<Dica nomes={{ inscricoes: 'Inscrições' }} />} />
          <Bar
            dataKey="inscricoes"
            fill="#2c2c2c"
            barSize={12}
            radius={6}
            background={{ fill: '#e9e5da', radius: 6 }}
          />
        </BarChart>
      </ResponsiveContainer>
      <p className="legenda">Abaixo de 6,00 a inscrição está em risco por média.</p>
    </section>
  );
}

export function Dispersao({ painel }: { painel: Painel }) {
  const pontos = (s: Situacao) =>
    painel.dispersao
      .filter((p) => p.situacao === s)
      .map((p) => ({ ...p, x: Number(p.frequencia), y: Number(p.media) }));
  const pearson = numero(painel.correlacao_frequencia_media);

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Frequência × média</h2>
          <p className="cartao-sub">Cada ponto é uma inscrição (aluno em uma disciplina)</p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke={GRADE} strokeDasharray="3 4" />
          <XAxis
            type="number"
            dataKey="x"
            name="Frequência"
            unit="%"
            domain={[50, 100]}
            ticks={[50, 60, 70, 80, 90, 100]}
            tick={EIXO}
            tickLine={false}
            axisLine={false}
          />
          <YAxis type="number" dataKey="y" name="Média" domain={[0, 10]} tick={EIXO} tickLine={false} axisLine={false} />
          <ZAxis range={[36, 36]} />
          <ReferenceLine x={75} stroke="#c9c4b6" strokeDasharray="4 4" />
          <ReferenceLine y={6} stroke="#c9c4b6" strokeDasharray="4 4" />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              const ponto = payload?.[0]?.payload as (Painel['dispersao'][number] | undefined);
              if (!active || !ponto) return null;
              return (
                <div className="dica">
                  <strong>{ponto.aluno}</strong>
                  <div>{ponto.disciplina}</div>
                  <div className="num">
                    Média {formatarNota(ponto.media)} · Frequência {formatarPercentual(ponto.frequencia)}
                  </div>
                </div>
              );
            }}
          />
          {SITUACOES_DO_GRAFICO.map((s) => (
            <Scatter key={s} name={ROTULO_SITUACAO[s]} data={pontos(s)} fill={COR_SITUACAO[s]} fillOpacity={0.85} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
      <p className="legenda">
        Linhas tracejadas: 75% e 6,00.
        {pearson !== null && ` Correlação de Pearson r = ${formatarNota(pearson)} (associação, não causa).`}
      </p>
    </section>
  );
}

function AlunosPrioritarios({ painel }: { painel: Painel }) {
  const alunos = painel.alunos
    .filter((a) => a.situacao === 'em_risco' || a.situacao === 'atencao')
    .sort(
      (a, b) =>
        ORDEM_SITUACAO.indexOf(a.situacao) - ORDEM_SITUACAO.indexOf(b.situacao) ||
        (numero(a.media) ?? 0) - (numero(b.media) ?? 0),
    );

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Alunos que precisam de acompanhamento</h2>
          <p className="cartao-sub">
            {alunos.length} alunos em risco ou em atenção, do mais crítico para o menos crítico
          </p>
        </div>
        <Link to="/alunos" className="botao-texto">
          Ver todos <ArrowRight size={13} />
        </Link>
      </div>
      <div className="lista">
        {alunos.slice(0, 6).map((aluno) => {
          const critica =
            aluno.inscricoes.find((i) => i.situacao === 'em_risco') ??
            aluno.inscricoes.find((i) => i.situacao === 'atencao')!;
          // "POO: média 4,50 (< 6,00) — media_baixa" → "média 4,50 (< 6,00)"
          const motivo = critica.justificativa
            .split(': ')
            .slice(1)
            .join(': ')
            .replace(/ — \w+/g, '');
          return (
            <div className="lista-linha" key={aluno.id}>
              <span className="avatar">{iniciais(aluno.nome)}</span>
              <div>
                <strong>{aluno.nome}</strong>
                <small className="num">{aluno.matricula}</small>
              </div>
              <div className="esconde-mobile">
                <strong>{critica.disciplina_nome}</strong>
                <small>{motivo}</small>
              </div>
              <span className="direita num esconde-mobile">{formatarNota(aluno.media)}</span>
              <span className="direita num esconde-mobile">{formatarPercentual(aluno.frequencia)}</span>
              <span className="direita">
                <Selo situacao={aluno.situacao} />
              </span>
            </div>
          );
        })}
        {alunos.length === 0 && <p className="vazio">Nenhum aluno em risco ou em atenção.</p>}
      </div>
    </section>
  );
}

function SituacaoAcademica({ painel }: { painel: Painel }) {
  const total = painel.total_alunos || 1;
  const corEscura: Record<Situacao, string> = {
    sem_risco: '#5f7a45',
    atencao: '#b88a1c',
    indeterminado: '#4a50d6',
    em_risco: '#d3532c',
  };

  return (
    <section className="cartao situacao">
      <div>
        <h2>Situação acadêmica</h2>
        <p className="cartao-sub">Risco calculado por disciplina e consolidado por aluno</p>
      </div>

      <div className="cartao">
        <div className="cartao-topo">
          <div>
            <h2>Inscrições por disciplina e turma</h2>
            <p className="cartao-sub">Quantidade de inscrições em cada situação</p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={painel.situacao_por_oferta} margin={{ top: 4, right: 4, bottom: 0, left: -24 }} barGap={3}>
            <CartesianGrid vertical={false} stroke={GRADE} strokeDasharray="3 4" />
            <XAxis dataKey="oferta" tick={EIXO} tickLine={false} axisLine={false} interval={0} />
            <YAxis allowDecimals={false} tick={EIXO} tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: 'rgb(0 0 0 / 0.04)' }} content={<Dica nomes={ROTULO_SITUACAO} />} />
            {SITUACOES_DO_GRAFICO.map((s) => (
              <Bar key={s} dataKey={s} fill={COR_SITUACAO[s]} barSize={6} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
        <div className="legenda">
          {SITUACOES_DO_GRAFICO.map((s) => (
            <span key={s}>
              <span className="ponto" style={{ color: COR_SITUACAO[s] }} /> {ROTULO_SITUACAO[s]}
            </span>
          ))}
        </div>
      </div>

      <div className="blocos">
        {SITUACOES_DO_GRAFICO.map((s) => (
          <div className={`bloco ${s}`} key={s}>
            <h3>{ROTULO_SITUACAO[s]}</h3>
            <Anel percentual={(painel.contagem[s] / total) * 100} cor={corEscura[s]} legenda="dos alunos" />
            <p className="bloco-rodape num">
              {painel.contagem[s]} <span>{painel.contagem[s] === 1 ? 'aluno' : 'alunos'}</span>
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function VisaoGeral({ painel }: { painel: Painel }) {
  return (
    <div className="visao">
      <div className="coluna">
        <Indicadores painel={painel} />
        <div className="graficos">
          <DistribuicaoMedias histograma={painel.histograma} />
          <Dispersao painel={painel} />
        </div>
        <AlunosPrioritarios painel={painel} />
      </div>
      <SituacaoAcademica painel={painel} />
    </div>
  );
}
