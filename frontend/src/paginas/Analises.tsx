import { useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { api } from '../api/cliente';
import type { Indicadores, Resposta, Situacao } from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';
import { Dica } from '../componentes/Dica';
import { COR_SITUACAO, formatarNota, formatarPercentual, numero, ROTULO_SITUACAO } from '../dados/formato';
import { DistribuicaoMedias, EIXO, GRADE } from './VisaoGeral';

type Janela = 'acumulado' | 'N1';

interface Props {
  turmaId: number | null;
  periodo: string | null;
}

function rotuloDisciplina(d: Indicadores['por_disciplina'][number]): string {
  return `${d.disciplina} · ${d.turma.split(' ').at(-1)}`;
}

function Estatisticas({ dados }: { dados: Indicadores }) {
  const { media, frequencia } = dados;
  const celulas: [string, string, string?][] = [
    ['Média', formatarNota(media.media)],
    ['Mediana', formatarNota(media.mediana)],
    ['Desvio padrão', formatarNota(media.desvio_padrao), media.observacao ?? undefined],
    ['Variância', formatarNota(media.variancia), media.tipo_variancia],
    ['Menor média', formatarNota(media.minimo)],
    ['Maior média', formatarNota(media.maximo)],
    ['Frequência média', formatarPercentual(frequencia.media)],
    ['Correlação frequência × média', formatarNota(dados.correlacao_frequencia_media), 'Pearson'],
  ];
  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Estatística descritiva das médias</h2>
          <p className="cartao-sub">
            {dados.inscricoes_validas} inscrições com dados
            {dados.inscricoes_sem_dados > 0 && `; ${dados.inscricoes_sem_dados} sem dados ficaram de fora`}
          </p>
        </div>
      </div>
      <div className="estatisticas">
        {celulas.map(([rotulo, valor, nota]) => (
          <div key={rotulo}>
            <span>{rotulo}</span>
            <strong className="num">{valor}</strong>
            {nota && <small>{nota}</small>}
          </div>
        ))}
      </div>
    </section>
  );
}

function Ranking({ dados }: { dados: Indicadores }) {
  const linhas = dados.por_disciplina.map((d) => ({ nome: rotuloDisciplina(d), media: numero(d.media) }));
  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Ranking de disciplinas</h2>
          <p className="cartao-sub">Média das inscrições de cada disciplina, da maior para a menor</p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={Math.max(160, linhas.length * 40)}>
        <BarChart data={linhas} layout="vertical" margin={{ top: 0, right: 40, bottom: 0, left: 0 }}>
          <XAxis type="number" domain={[0, 10]} hide />
          <YAxis type="category" dataKey="nome" width={200} tick={EIXO} tickLine={false} axisLine={false} />
          <Bar dataKey="media" fill="#2c2c2c" barSize={12} radius={6} background={{ fill: '#e9e5da', radius: 6 }}>
            <LabelList dataKey="media" position="right" formatter={(v) => formatarNota(v as number)} className="num" fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}

function Evolucao({ dados }: { dados: Indicadores }) {
  const linhas = dados.por_disciplina.map((d) => ({
    nome: d.oferta,
    N1: numero(d.media_n1),
    Acumulado: numero(d.media),
  }));
  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Evolução por disciplina</h2>
          <p className="cartao-sub">Média só da N1 comparada à média acumulada (N1 + N2)</p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={linhas} margin={{ top: 4, right: 4, bottom: 0, left: -18 }} barGap={4}>
          <CartesianGrid vertical={false} stroke={GRADE} strokeDasharray="3 4" />
          <XAxis dataKey="nome" tick={EIXO} tickLine={false} axisLine={false} interval={0} />
          <YAxis domain={[0, 10]} tick={EIXO} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: 'rgb(0 0 0 / 0.04)' }} content={<Dica formatar={(v) => formatarNota(v)} />} />
          <Bar dataKey="N1" fill="#c9c4b6" barSize={14} radius={[4, 4, 0, 0]} />
          <Bar dataKey="Acumulado" fill="#2c2c2c" barSize={14} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="legenda">
        <span>
          <span className="ponto" style={{ color: '#c9c4b6' }} /> N1
        </span>
        <span>
          <span className="ponto" style={{ color: '#2c2c2c' }} /> Acumulado
        </span>
      </div>
    </section>
  );
}

function SituacaoInscricoes({ dados }: { dados: Indicadores }) {
  const total = Object.values(dados.situacao_inscricoes).reduce((a, b) => a + b, 0) || 1;
  const ordem: Situacao[] = ['em_risco', 'atencao', 'sem_risco', 'indeterminado'];
  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Situação das inscrições</h2>
          <p className="cartao-sub">Risco por disciplina, antes de consolidar por aluno</p>
        </div>
      </div>
      <div className="barras-situacao">
        {ordem.map((s) => (
          <div key={s}>
            <span>{ROTULO_SITUACAO[s]}</span>
            <div className="trilho">
              <div style={{ width: `${(dados.situacao_inscricoes[s] / total) * 100}%`, background: COR_SITUACAO[s] }} />
            </div>
            <strong className="num">{dados.situacao_inscricoes[s]}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Analises({ turmaId, periodo }: Props) {
  const [janela, setJanela] = useState<Janela>('acumulado');
  const caminho = turmaId
    ? `/analitico/indicadores/turmas/${turmaId}`
    : `/analitico/indicadores/periodos/${encodeURIComponent(periodo ?? '')}`;
  const indicadores = useDados(
    () => api<Resposta<Indicadores>>(`${caminho}?janela=${janela}`).then((r) => r.dados),
    [caminho, janela],
  );

  if (!turmaId && !periodo) {
    return <p className="vazio">Cadastre uma turma para ver as análises.</p>;
  }

  return (
    <div className="analises">
      <div className="ferramentas">
        <div className="segmentos" role="group" aria-label="Janela de análise">
          {(
            [
              ['acumulado', 'Acumulado (N1 + N2)'],
              ['N1', 'Parcial (só N1)'],
            ] as const
          ).map(([valor, rotulo]) => (
            <button key={valor} type="button" aria-pressed={janela === valor} onClick={() => setJanela(valor)}>
              {rotulo}
            </button>
          ))}
        </div>
        <p className="cartao-sub">
          {janela === 'N1'
            ? 'Janela parcial: a variância é amostral (÷ n − 1), porque é um recorte do semestre.'
            : 'Semestre completo: a variância é populacional (÷ n).'}
        </p>
      </div>
      <Conteudo estado={indicadores}>
        {(dados) => (
          <div className="coluna">
            <Estatisticas dados={dados} />
            <div className="graficos">
              <Ranking dados={dados} />
              <Evolucao dados={dados} />
            </div>
            <div className="graficos">
              <DistribuicaoMedias histograma={dados.histograma} />
              <SituacaoInscricoes dados={dados} />
            </div>
            <p className="cartao-sub">
              Os indicadores descrevem os dados lançados; não são previsão de reprovação.
            </p>
          </div>
        )}
      </Conteudo>
    </div>
  );
}
