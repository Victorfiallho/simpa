import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Anel } from '../componentes/Anel';
import { Dica } from '../componentes/Dica';
import { Selo } from '../componentes/Selo';
import {
  COR_STATUS,
  descreverCriterio,
  formatarDecimal,
  formatarNota,
  formatarPercentual,
  iniciais,
  ORDEM_STATUS,
  ROTULO_STATUS,
} from '../dados/formato';
import type { Painel } from '../dados/painel';
import type { Status } from '../dados/tipos';

const EIXO = { fontSize: 11, fill: '#8b887f' };
const GRADE = '#e2ddd0';

function Variacao({ valor, sufixo }: { valor: number | null; sufixo: string }) {
  if (valor === null) return null;
  const sobe = valor >= 0;
  return (
    <div className="kpi-rodape">
      <span className={`variacao ${sobe ? 'sobe' : 'desce'}`}>
        {sobe ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
      </span>
      <span className="num">
        {sobe ? '+' : '−'}
        {formatarNota(Math.abs(valor))}
      </span>
      {sufixo}
    </div>
  );
}

function Indicadores({ painel }: { painel: Painel }) {
  const variacaoMedia =
    painel.mediaGeral !== null && painel.mediaGeralN1 !== null
      ? painel.mediaGeral - painel.mediaGeralN1
      : null;
  const variacaoFrequencia =
    painel.frequenciaRecente !== null && painel.frequenciaGeral !== null
      ? painel.frequenciaRecente - painel.frequenciaGeral
      : null;

  return (
    <section className="cartao kpis" aria-label="Indicadores gerais">
      <div className="kpi">
        <p className="kpi-rotulo">Alunos acompanhados</p>
        <p className="kpi-valor num">{painel.alunos.length}</p>
        <div className="kpi-rodape">{painel.totalInscricoes} inscrições em 3 disciplinas</div>
      </div>
      <div className="kpi">
        <p className="kpi-rotulo">Média geral</p>
        <p className="kpi-valor num">
          {formatarNota(painel.mediaGeral)}
          <small>/ 10</small>
        </p>
        <Variacao valor={variacaoMedia} sufixo="em relação à N1" />
      </div>
      <div className="kpi">
        <p className="kpi-rotulo">Frequência média</p>
        <p className="kpi-valor num">
          {formatarNota(painel.frequenciaGeral)}
          <small>%</small>
        </p>
        <Variacao valor={variacaoFrequencia} sufixo="p.p. no último mês" />
      </div>
    </section>
  );
}

function DistribuicaoMedias({ painel }: { painel: Painel }) {
  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Distribuição das médias</h2>
          <p className="cartao-sub">Inscrições por faixa de média final</p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={210}>
        <BarChart data={painel.histograma} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
          <CartesianGrid vertical={false} stroke={GRADE} strokeDasharray="3 4" />
          <XAxis dataKey="faixa" tick={EIXO} tickLine={false} axisLine={false} interval={0} />
          <YAxis allowDecimals={false} tick={EIXO} tickLine={false} axisLine={false} />
          <Tooltip
            cursor={{ fill: 'rgb(0 0 0 / 0.04)' }}
            content={<Dica nomes={{ inscricoes: 'Inscrições' }} />}
          />
          <Bar
            dataKey="inscricoes"
            fill="#2c2c2c"
            barSize={12}
            radius={6}
            background={{ fill: '#e9e5da', radius: 6 }}
          />
        </BarChart>
      </ResponsiveContainer>
      <div className="legenda">
        <span>Média mínima para aprovação: 6,00</span>
      </div>
    </section>
  );
}

function FrequenciaSemanal({ painel }: { painel: Painel }) {
  const mostrarA = painel.frequenciaSemanal.some((s) => s.A !== null);
  const mostrarB = painel.frequenciaSemanal.some((s) => s.B !== null);
  const nomes = { A: 'Turma A', B: 'Turma B' };

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Frequência semanal</h2>
          <p className="cartao-sub">Presença por semana do período letivo</p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={210}>
        <LineChart data={painel.frequenciaSemanal} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid vertical={false} stroke={GRADE} strokeDasharray="3 4" />
          <XAxis dataKey="semana" tick={EIXO} tickLine={false} axisLine={false} interval={1} />
          <YAxis
            domain={[60, 100]}
            ticks={[60, 70, 80, 90, 100]}
            tick={EIXO}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ stroke: '#c9c4b6' }}
            content={<Dica nomes={nomes} formatar={(v) => `${formatarDecimal(v)}%`} />}
          />
          {mostrarA && (
            <Line type="monotone" dataKey="A" stroke="#8ca573" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
          )}
          {mostrarB && (
            <Line type="monotone" dataKey="B" stroke="#e1ba58" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
          )}
        </LineChart>
      </ResponsiveContainer>
      <div className="legenda">
        {mostrarA && (
          <span>
            <span className="ponto" style={{ color: '#8ca573' }} /> Turma A
          </span>
        )}
        {mostrarB && (
          <span>
            <span className="ponto" style={{ color: '#e1ba58' }} /> Turma B
          </span>
        )}
      </div>
    </section>
  );
}

function AlunosPrioritarios({ painel }: { painel: Painel }) {
  const prioridade = (s: Status) => ORDEM_STATUS.indexOf(s);
  const alunos = painel.alunos
    .filter((a) => a.status === 'em_risco' || a.status === 'atencao')
    .sort(
      (a, b) =>
        prioridade(a.status) - prioridade(b.status) ||
        (a.media ?? 0) - (b.media ?? 0),
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
            aluno.resumos.find((r) => r.status === 'em_risco') ??
            aluno.resumos.find((r) => r.status === 'atencao')!;
          const motivo = critica.criterios.length
            ? critica.criterios
                .map((c) => descreverCriterio(c, critica.media, critica.frequencia))
                .join(' e ')
            : 'próximo do limite mínimo';
          return (
            <div className="lista-linha" key={aluno.id}>
              <span className="avatar">{iniciais(aluno.nome)}</span>
              <div>
                <strong>{aluno.nome}</strong>
                <small className="num">{aluno.matricula}</small>
              </div>
              <div className="esconde-mobile">
                <strong>{critica.disciplina.nome}</strong>
                <small>{motivo}</small>
              </div>
              <span className="direita num esconde-mobile">{formatarNota(aluno.media)}</span>
              <span className="direita num esconde-mobile">
                {formatarPercentual(aluno.frequencia)}
              </span>
              <span className="direita">
                <Selo status={aluno.status} />
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
  const total = painel.alunos.length || 1;
  const blocos: { status: Status; legenda: string }[] = [
    { status: 'sem_risco', legenda: 'dos alunos' },
    { status: 'atencao', legenda: 'dos alunos' },
    { status: 'indeterminado', legenda: 'dos alunos' },
    { status: 'em_risco', legenda: 'dos alunos' },
  ];
  const corEscura: Record<Status, string> = {
    sem_risco: '#5f7a45',
    atencao: '#b88a1c',
    indeterminado: '#4a50d6',
    em_risco: '#d3532c',
  };

  return (
    <section className="cartao situacao">
      <div>
        <h2>Situação acadêmica</h2>
        <p className="cartao-sub">Classificação de risco por disciplina e por aluno</p>
      </div>

      <div className="cartao">
        <div className="cartao-topo">
          <div>
            <h2>Inscrições por disciplina e turma</h2>
            <p className="cartao-sub">Quantidade de inscrições em cada situação</p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={painel.situacaoPorOferta}
            margin={{ top: 4, right: 4, bottom: 0, left: -24 }}
            barGap={3}
          >
            <CartesianGrid vertical={false} stroke={GRADE} strokeDasharray="3 4" />
            <XAxis dataKey="oferta" tick={EIXO} tickLine={false} axisLine={false} interval={0} />
            <YAxis allowDecimals={false} tick={EIXO} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: 'rgb(0 0 0 / 0.04)' }}
              content={<Dica nomes={ROTULO_STATUS} />}
            />
            {(['sem_risco', 'atencao', 'indeterminado', 'em_risco'] as Status[]).map((s) => (
              <Bar key={s} dataKey={s} fill={COR_STATUS[s]} barSize={6} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
        <div className="legenda">
          {(['sem_risco', 'atencao', 'indeterminado', 'em_risco'] as Status[]).map((s) => (
            <span key={s}>
              <span className="ponto" style={{ color: COR_STATUS[s] }} /> {ROTULO_STATUS[s]}
            </span>
          ))}
        </div>
      </div>

      <div className="blocos">
        {blocos.map(({ status, legenda }) => (
          <div className={`bloco ${status}`} key={status}>
            <h3>{ROTULO_STATUS[status]}</h3>
            <Anel
              percentual={(painel.contagem[status] / total) * 100}
              cor={corEscura[status]}
              legenda={legenda}
            />
            <p className="bloco-rodape num">
              {painel.contagem[status]} <span>{painel.contagem[status] === 1 ? 'aluno' : 'alunos'}</span>
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
          <DistribuicaoMedias painel={painel} />
          <FrequenciaSemanal painel={painel} />
        </div>
        <AlunosPrioritarios painel={painel} />
      </div>
      <SituacaoAcademica painel={painel} />
    </div>
  );
}
