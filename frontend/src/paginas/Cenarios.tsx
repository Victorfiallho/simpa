import { RotateCcw } from 'lucide-react';
import { useState } from 'react';

import { api } from '../api/cliente';
import type { BaseCenario, MargemCenario, ProjecaoCenario, Resposta } from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';
import { formatarNota, formatarPercentual } from '../dados/formato';

interface Regras {
  aprovacao: string;
  recuperacao: string;
  final: string;
}
const PADRAO: Regras = { aprovacao: '6', recuperacao: '4', final: '5' };

const ROTULO_VIABILIDADE: Record<string, { texto: string; classe: string }> = {
  aprovado_direto: { texto: 'Aprovado direto', classe: 'sem_risco' },
  garantida: { texto: 'Aprovação garantida', classe: 'sem_risco' },
  alcancavel: { texto: 'Alcançável', classe: 'sem_risco' },
  exige_esforco: { texto: 'Exige esforço', classe: 'atencao' },
  dificil: { texto: 'Difícil', classe: 'atencao' },
  inviavel: { texto: 'Inviável direto', classe: 'em_risco' },
  reprovacao_frequencia: { texto: 'Reprovação por frequência', classe: 'em_risco' },
  reprovacao_nota: { texto: 'Reprovação por nota', classe: 'em_risco' },
  sem_dados: { texto: 'Sem dados', classe: 'indeterminado' },
};
const ROTULO_RESULTADO: Record<string, string> = {
  direta: 'Aprovação direta',
  recuperacao: 'Recuperação',
  recuperado: 'Aprovado na recuperação',
  rep_nota: 'Reprovação por nota',
  rep_freq: 'Reprovação por frequência',
};

function Viabilidade({ codigo }: { codigo: string }) {
  const { texto, classe } = ROTULO_VIABILIDADE[codigo] ?? { texto: codigo, classe: 'indeterminado' };
  return (
    <span className={`selo ${classe}`}>
      <span className="ponto" aria-hidden="true" />
      {texto}
    </span>
  );
}

/** Valida como a API: de 0 a 10, com a recuperação até a aprovação. Devolve o motivo ou null. */
function motivoInvalido(r: Regras): string | null {
  const valores = [r.aprovacao, r.recuperacao, r.final].map(Number);
  if (valores.some((v) => !Number.isFinite(v) || v < 0 || v > 10) || [r.aprovacao, r.recuperacao, r.final].includes('')) {
    return 'Use valores de 0 a 10.';
  }
  if (Number(r.recuperacao) > Number(r.aprovacao)) {
    return 'A média de recuperação não pode passar da média de aprovação.';
  }
  return null;
}

export function Cenarios({ turmaId, periodo }: { turmaId: number | null; periodo: string | null }) {
  const [regras, setRegras] = useState<Regras>(PADRAO);
  const [base, setBase] = useState<BaseCenario>('atual');
  const [escolhida, setEscolhida] = useState<number | null>(null);
  const invalido = motivoInvalido(regras);

  const consulta = new URLSearchParams({
    aprovacao: regras.aprovacao,
    recuperacao: regras.recuperacao,
    final: regras.final,
    base,
  });
  if (turmaId) consulta.set('turma_id', String(turmaId));
  if (periodo) consulta.set('periodo_letivo', periodo);

  const projecao = useDados(
    () =>
      invalido
        ? Promise.resolve<ProjecaoCenario | null>(null)
        : api<Resposta<ProjecaoCenario>>(`/analitico/cenarios/projecao?${consulta}`).then((r) => r.dados),
    [consulta.toString(), invalido],
  );

  const campo = (rotulo: string, nome: keyof Regras) => (
    <label className="campo">
      {rotulo}
      <input
        type="number"
        min={0}
        max={10}
        step={0.1}
        value={regras[nome]}
        onChange={(e) => setRegras({ ...regras, [nome]: e.target.value })}
      />
    </label>
  );

  return (
    <div className="coluna">
      <section className="cartao">
        <div className="cartao-topo">
          <div>
            <h2>Regras de aprovação</h2>
            <p className="cartao-sub">
              Ajuste as médias e veja o efeito na turma. Nada é gravado: é uma simulação.
            </p>
          </div>
          <button type="button" className="botao-texto" onClick={() => setRegras(PADRAO)}>
            <RotateCcw size={14} aria-hidden="true" /> Restaurar padrão
          </button>
        </div>
        <div className="parametros">
          {campo('Média para aprovação direta', 'aprovacao')}
          {campo('Média mínima para recuperação', 'recuperacao')}
          {campo('Média final com recuperação', 'final')}
          <div className="segmentos" role="group" aria-label="Dados considerados">
            <button type="button" aria-pressed={base === 'n1'} onClick={() => setBase('n1')}>
              Projetar a partir da N1
            </button>
            <button type="button" aria-pressed={base === 'atual'} onClick={() => setBase('atual')}>
              Usar N1 e N2 lançadas
            </button>
          </div>
        </div>
        {invalido && (
          <p className="erro-campo" role="alert">
            {invalido}
          </p>
        )}
      </section>

      {!invalido && (
        <Conteudo estado={projecao}>
          {(p) =>
            p === null ? null : (
              <>
                <section className="cartao">
                  <div className="cartao-topo">
                    <div>
                      <h2>Projeção de retenção da turma</h2>
                      <p className="cartao-sub">
                        {p.inscricoes_projetadas} inscrições projetadas ·{' '}
                        {p.base === 'n1'
                          ? 'só a N1 conta; a N2 é estimada pela tendência da disciplina'
                          : 'resultado atual de cada aluno'}
                        . É uma estimativa, não uma previsão.
                      </p>
                    </div>
                  </div>
                  <div className="kpis" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
                    <div className="kpi">
                      <span className="kpi-rotulo">Aprovação direta</span>
                      <div className="kpi-valor num">{p.contagem.direta}</div>
                    </div>
                    <div className="kpi">
                      <span className="kpi-rotulo">Recuperação</span>
                      <div className="kpi-valor num">{p.contagem.recuperacao}</div>
                    </div>
                    <div className="kpi">
                      <span className="kpi-rotulo">Reprovação</span>
                      <div className="kpi-valor num">{p.contagem.rep_nota + p.contagem.rep_freq}</div>
                      <div className="kpi-rodape">
                        {p.contagem.rep_nota} por nota e {p.contagem.rep_freq} por frequência
                      </div>
                    </div>
                    <div className="kpi">
                      <span className="kpi-rotulo">Retenção projetada</span>
                      <div className="kpi-valor num">{formatarPercentual(p.retencao_percentual)}</div>
                      <div className="kpi-rodape">não aprovadas direto</div>
                    </div>
                  </div>
                  <p className="cartao-sub" style={{ marginTop: 16 }}>
                    Alunos: {p.alunos.aprovados_em_tudo} aprovados em tudo · {p.alunos.com_recuperacao} com ao
                    menos uma recuperação · {p.alunos.com_reprovacao} com ao menos uma reprovação.
                  </p>
                </section>

                <section className="cartao">
                  <div className="cartao-topo">
                    <div>
                      <h2>Projeção por disciplina e turma</h2>
                      <p className="cartao-sub">Quantas inscrições terminam em cada resultado.</p>
                    </div>
                  </div>
                  <div className="tabela-rolagem">
                    <table className="tabela">
                      <thead>
                        <tr>
                          <th>Oferta</th>
                          <th className="direita">Direta</th>
                          <th className="direita">Recuperação</th>
                          <th className="direita">Rep. por nota</th>
                          <th className="direita">Rep. por frequência</th>
                        </tr>
                      </thead>
                      <tbody>
                        {p.por_oferta.map((o) => (
                          <tr key={o.oferta}>
                            <td>{o.oferta}</td>
                            <td className="direita num">{o.direta}</td>
                            <td className="direita num">{o.recuperacao}</td>
                            <td className="direita num">{o.rep_nota}</td>
                            <td className="direita num">{o.rep_freq}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="cartao">
                  <div className="cartao-topo">
                    <div>
                      <h2>Metas de recuperação</h2>
                      <p className="cartao-sub">
                        {p.total_metas} inscrição(ões) de alunos em risco ou em atenção que ainda precisam de
                        uma meta. Clique em uma linha para simular uma nota.
                      </p>
                    </div>
                  </div>
                  {p.metas.length === 0 ? (
                    <p className="vazio">Nenhum aluno em risco precisa de meta neste recorte.</p>
                  ) : (
                    <div className="tabela-rolagem">
                      <table className="tabela">
                        <thead>
                          <tr>
                            <th>Aluno</th>
                            <th>Disciplina</th>
                            <th className="direita">N1</th>
                            <th className="direita">N2</th>
                            <th className="direita">Média</th>
                            <th className="direita">Frequência</th>
                            <th>Meta</th>
                            <th>Viabilidade</th>
                          </tr>
                        </thead>
                        <tbody>
                          {p.metas.map((m) => (
                            <tr
                              key={m.inscricao_id}
                              className={m.inscricao_id === escolhida ? 'selecionada' : undefined}
                              onClick={() => setEscolhida(m.inscricao_id)}
                              style={{ cursor: 'pointer' }}
                            >
                              <td>
                                <strong>{m.aluno_nome}</strong>
                                <br />
                                <small className="cartao-sub">{m.matricula}</small>
                              </td>
                              <td>{m.disciplina_nome}</td>
                              <td className="direita num">{formatarNota(m.n1)}</td>
                              <td className="direita num">{m.n2 === null ? '—' : formatarNota(m.n2)}</td>
                              <td className="direita num">{formatarNota(m.media)}</td>
                              <td className="direita num">{formatarPercentual(m.frequencia)}</td>
                              <td>{m.meta}</td>
                              <td>
                                <Viabilidade codigo={m.viabilidade} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>

                {escolhida !== null && <Calculadora inscricaoId={escolhida} regras={regras} base={base} />}
              </>
            )
          }
        </Conteudo>
      )}
    </div>
  );
}

function Calculadora({ inscricaoId, regras, base }: { inscricaoId: number; regras: Regras; base: BaseCenario }) {
  const [hipotese, setHipotese] = useState('');
  const hipoteseValida = hipotese !== '' && Number(hipotese) >= 0 && Number(hipotese) <= 10;
  const consulta = new URLSearchParams({
    aprovacao: regras.aprovacao,
    recuperacao: regras.recuperacao,
    final: regras.final,
    base,
  });
  if (hipoteseValida) consulta.set('hipotese', hipotese);

  const margem = useDados(
    () => api<Resposta<MargemCenario>>(`/analitico/cenarios/margem/${inscricaoId}?${consulta}`).then((r) => r.dados),
    [inscricaoId, consulta.toString()],
  );

  return (
    <section className="cartao" aria-live="polite">
      <div className="cartao-topo">
        <div>
          <h2>Calculadora de margem</h2>
          <p className="cartao-sub">Nota mínima que falta para aprovar e o efeito de uma nota hipotética.</p>
        </div>
      </div>
      <Conteudo estado={margem}>
        {(m) => (
          <div className="coluna">
            <p>
              <strong>{m.aluno_nome}</strong> · {m.disciplina_nome} <Viabilidade codigo={m.viabilidade} />
            </p>
            <p>{m.meta}</p>
            {(m.modo === 'n2' || m.modo === 'exame') && (
              <label className="campo campo-linha">
                E se tirar na {m.modo === 'n2' ? 'N2' : 'recuperação'}?
                <input
                  type="number"
                  min={0}
                  max={10}
                  step={0.1}
                  value={hipotese}
                  placeholder="0 a 10"
                  onChange={(e) => setHipotese(e.target.value)}
                />
              </label>
            )}
            {m.hipotese_resultado && (
              <p>
                Com {formatarNota(hipotese)}: média{' '}
                {m.modo === 'exame' ? 'final ' : ''}
                {formatarNota(m.hipotese_media)} →{' '}
                <strong>{ROTULO_RESULTADO[m.hipotese_resultado] ?? m.hipotese_resultado}</strong>.
              </p>
            )}
          </div>
        )}
      </Conteudo>
    </section>
  );
}
