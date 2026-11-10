import { Save } from 'lucide-react';
import { useEffect, useState } from 'react';

import { api } from '../api/cliente';
import type {
  AlunoCadastro,
  DisciplinaCadastro,
  FrequenciaLancada,
  InscricaoCadastro,
  NotaLancada,
  RespostaPaginada,
  TurmaCadastro,
} from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';

// Lançamento de notas e frequência (RF03) para admin e professor. O professor só enxerga as próprias
// disciplinas: quem recusa o resto é o backend (D03), a tela só mostra o que ele devolve.

const PERIODOS = ['N1', 'N2'] as const;
type Periodo = (typeof PERIODOS)[number];

const TIPOS = [
  ['prova', 'Prova'],
  ['trabalho', 'Trabalho'],
  ['atividade', 'Atividade'],
  ['projeto', 'Projeto'],
  ['seminario', 'Seminário'],
] as const;

const PESO_PADRAO: Record<Periodo, string> = { N1: '4', N2: '6' };
const AULAS_PADRAO = '32';
const LIMITE = 100;

interface Dados {
  disciplinaId: number;
  inscricoes: InscricaoCadastro[];
  alunos: AlunoCadastro[];
  notas: NotaLancada[];
  frequencias: FrequenciaLancada[];
  truncado: boolean;
}

/** O que está digitado em uma linha: uma nota e uma quantidade de faltas por período. */
type Edicao = Record<`nota_${Periodo}` | `faltas_${Periodo}`, string>;

const normalizar = (texto: string) => texto.trim().replace(',', '.');
const mostrar = (valor: string) => String(Number(valor)).replace('.', ',');

export function Lancamentos() {
  const [disciplinaId, setDisciplinaId] = useState('');
  const turmas = useDados(
    () =>
      api<RespostaPaginada<TurmaCadastro>>('/academico/turmas?limite=100&ordenar_por=nome').then(
        (r) => r.dados,
      ),
    [],
  );
  const disciplinas = useDados(
    () =>
      api<RespostaPaginada<DisciplinaCadastro>>(
        `/academico/disciplinas?limite=${LIMITE}&status=ativa&ordenar_por=nome`,
      ).then((r) => r.dados),
    [],
  );
  const disciplina = disciplinas.dados?.find((d) => String(d.id) === disciplinaId) ?? null;
  const nomeTurma = (id: number) => turmas.dados?.find((t) => t.id === id)?.nome ?? `Turma ${id}`;

  const dados = useDados<Dados | null>(async () => {
    if (!disciplina) return null;
    const d = disciplina.id;
    const [inscricoes, alunos, notas, frequencias] = await Promise.all([
      api<RespostaPaginada<InscricaoCadastro>>(
        `/academico/inscricoes?disciplina_id=${d}&status=ativa&limite=${LIMITE}&ordenar_por=id`,
      ),
      api<RespostaPaginada<AlunoCadastro>>(
        `/academico/alunos?turma_id=${disciplina.turma_id}&limite=${LIMITE}&ordenar_por=nome_completo`,
      ),
      api<RespostaPaginada<NotaLancada>>(`/academico/avaliacoes?disciplina_id=${d}&limite=${LIMITE}`),
      api<RespostaPaginada<FrequenciaLancada>>(`/academico/frequencias?disciplina_id=${d}&limite=${LIMITE}`),
    ]);
    return {
      disciplinaId: d,
      inscricoes: inscricoes.dados,
      alunos: alunos.dados,
      notas: notas.dados,
      frequencias: frequencias.dados,
      truncado: [inscricoes, notas, frequencias].some((r) => r.total_registros > LIMITE),
    };
  }, [disciplinaId]);

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Lançamento de notas e frequência</h2>
          <p className="cartao-sub">
            Escolha a disciplina, preencha e salve. O risco de cada aluno é recalculado automaticamente.
          </p>
        </div>
      </div>
      <Conteudo estado={disciplinas}>
        {(lista) => (
          <>
            <div className="ferramentas">
              <label className="campo-linha">
                Disciplina
                <select value={disciplinaId} onChange={(e) => setDisciplinaId(e.target.value)}>
                  <option value="">Selecione…</option>
                  {lista.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.nome} · {nomeTurma(d.turma_id)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {lista.length === 0 && <p className="vazio">Nenhuma disciplina disponível para o seu perfil.</p>}
            {disciplina && (
              <Conteudo estado={dados}>
                {(carregado) =>
                  // Ao trocar de disciplina, os dados antigos ainda ficam um instante: não os mostre.
                  carregado?.disciplinaId === disciplina.id && (
                    <Planilha key={disciplina.id} dados={carregado} aoSalvar={dados.recarregar} />
                  )
                }
              </Conteudo>
            )}
          </>
        )}
      </Conteudo>
    </section>
  );
}

function Planilha({ dados, aoSalvar }: { dados: Dados; aoSalvar: () => void }) {
  const { inscricoes, alunos, notas, frequencias } = dados;
  const nota = (inscricaoId: number, p: Periodo) =>
    notas.filter((n) => n.inscricao_id === inscricaoId && n.periodo_avaliacao === p);
  const frequencia = (inscricaoId: number, p: Periodo) =>
    frequencias.find((f) => f.inscricao_id === inscricaoId && f.periodo_avaliacao === p);

  const valoresSalvos = (inscricaoId: number): Edicao => {
    const e = {} as Edicao;
    for (const p of PERIODOS) {
      const n = nota(inscricaoId, p);
      e[`nota_${p}`] = n.length === 1 ? mostrar(n[0].nota) : '';
      e[`faltas_${p}`] = String(frequencia(inscricaoId, p)?.faltas ?? '');
    }
    return e;
  };

  // Parâmetros para os lançamentos novos; começam do que já existe na disciplina.
  const [tipo, setTipo] = useState('prova');
  const pesoInicial = (p: Periodo) => {
    const existente = notas.find((n) => n.periodo_avaliacao === p);
    return existente ? String(Number(existente.peso)) : PESO_PADRAO[p];
  };
  const [pesos, setPesos] = useState<Record<Periodo, string>>({ N1: pesoInicial('N1'), N2: pesoInicial('N2') });
  const [aulas, setAulas] = useState<Record<Periodo, string>>({
    N1: String(frequencias.find((f) => f.periodo_avaliacao === 'N1')?.aulas_previstas ?? AULAS_PADRAO),
    N2: String(frequencias.find((f) => f.periodo_avaliacao === 'N2')?.aulas_previstas ?? AULAS_PADRAO),
  });

  const [edicoes, setEdicoes] = useState<Record<number, Edicao>>({});
  const [erros, setErros] = useState<Record<number, string>>({});
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  // Depois de salvar e recarregar, as digitações antigas deixam de valer.
  useEffect(() => {
    setEdicoes({});
  }, [notas, frequencias]);

  const atual = (id: number): Edicao => edicoes[id] ?? valoresSalvos(id);
  const alterada = (id: number) => {
    const a = atual(id);
    const s = valoresSalvos(id);
    return (Object.keys(s) as (keyof Edicao)[]).some((k) => a[k] !== s[k]);
  };
  const sujas = inscricoes.filter((i) => alterada(i.id));

  function digitar(id: number, campo: keyof Edicao, valor: string) {
    setAviso(null);
    setEdicoes((e) => ({ ...e, [id]: { ...atual(id), [campo]: valor } }));
  }

  /** Salva uma linha. Devolve quantos lançamentos foram gravados ou lança o erro da primeira falha. */
  async function salvarLinha(inscricao: InscricaoCadastro): Promise<number> {
    const e = atual(inscricao.id);
    const s = valoresSalvos(inscricao.id);
    let gravados = 0;
    for (const p of PERIODOS) {
      const campoNota = `nota_${p}` as const;
      if (e[campoNota] !== s[campoNota] && e[campoNota].trim() !== '') {
        const valor = normalizar(e[campoNota]);
        if (!(Number(valor) >= 0 && Number(valor) <= 10)) throw new Error(`Nota ${p}: use um valor de 0 a 10.`);
        const existente = nota(inscricao.id, p)[0];
        if (existente) {
          await api(`/academico/avaliacoes/${existente.id}`, { method: 'PATCH', body: JSON.stringify({ nota: valor }) });
        } else {
          await api('/academico/avaliacoes', {
            method: 'POST',
            body: JSON.stringify({
              inscricao_id: inscricao.id,
              tipo_avaliacao: tipo,
              periodo_avaliacao: p,
              nota: valor,
              peso: normalizar(pesos[p]),
            }),
          });
        }
        gravados += 1;
      }
      const campoFaltas = `faltas_${p}` as const;
      if (e[campoFaltas] !== s[campoFaltas] && e[campoFaltas].trim() !== '') {
        const faltas = Number(e[campoFaltas]);
        const existente = frequencia(inscricao.id, p);
        const previstas = existente?.aulas_previstas ?? Number(aulas[p]);
        if (!Number.isInteger(faltas) || faltas < 0 || faltas > previstas) {
          throw new Error(`Faltas ${p}: use um número inteiro de 0 a ${previstas}.`);
        }
        if (existente) {
          await api(`/academico/frequencias/${existente.id}`, { method: 'PATCH', body: JSON.stringify({ faltas }) });
        } else {
          await api('/academico/frequencias', {
            method: 'POST',
            body: JSON.stringify({
              inscricao_id: inscricao.id,
              periodo_avaliacao: p,
              aulas_previstas: previstas,
              faltas,
            }),
          });
        }
        gravados += 1;
      }
    }
    return gravados;
  }

  async function salvar(linhas: InscricaoCadastro[]) {
    setSalvando(true);
    setAviso(null);
    const novosErros: Record<number, string> = {};
    let total = 0;
    for (const inscricao of linhas) {
      try {
        total += await salvarLinha(inscricao);
      } catch (err) {
        novosErros[inscricao.id] = (err as Error).message;
      }
    }
    setErros(novosErros);
    setSalvando(false);
    const comErro = Object.keys(novosErros).length;
    setAviso(
      comErro
        ? `${total} lançamento(s) salvo(s). ${comErro} linha(s) com erro, veja os avisos em vermelho.`
        : `${total} lançamento(s) salvo(s). O risco dos alunos foi recalculado.`,
    );
    aoSalvar();
  }

  const nomeAluno = (id: number) => alunos.find((a) => a.id === id);

  return (
    <>
      {dados.truncado && (
        <p className="aviso" role="status">
          Esta disciplina tem mais de {LIMITE} registros; só os primeiros {LIMITE} aparecem.
        </p>
      )}
      <div className="parametros">
        <label className="campo">
          Tipo da avaliação (novos lançamentos)
          <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
            {TIPOS.map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </label>
        {PERIODOS.map((p) => (
          <label className="campo" key={`peso-${p}`}>
            Peso {p}
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={pesos[p]}
              onChange={(e) => setPesos({ ...pesos, [p]: e.target.value })}
            />
          </label>
        ))}
        {PERIODOS.map((p) => (
          <label className="campo" key={`aulas-${p}`}>
            Aulas previstas {p}
            <input
              type="number"
              min="1"
              step="1"
              value={aulas[p]}
              onChange={(e) => setAulas({ ...aulas, [p]: e.target.value })}
            />
          </label>
        ))}
      </div>
      <p className="cartao-sub">
        Peso e aulas previstas valem só para lançamentos novos. Campo vazio não apaga o que já foi lançado.
      </p>

      {aviso && (
        <p className={Object.keys(erros).length ? 'aviso' : 'aviso-sucesso'} role="status">
          {aviso}
        </p>
      )}

      {inscricoes.length === 0 ? (
        <p className="vazio">Nenhum aluno com inscrição ativa nesta disciplina.</p>
      ) : (
        <>
          <div className="tabela-rolagem">
            <table className="tabela planilha">
              <thead>
                <tr>
                  <th>Aluno</th>
                  {PERIODOS.map((p) => (
                    <th key={`n-${p}`}>Nota {p}</th>
                  ))}
                  {PERIODOS.map((p) => (
                    <th key={`f-${p}`}>Faltas {p}</th>
                  ))}
                  <th className="direita">Ação</th>
                </tr>
              </thead>
              <tbody>
                {inscricoes.map((i) => {
                  const aluno = nomeAluno(i.aluno_id);
                  const e = atual(i.id);
                  const suja = alterada(i.id);
                  return (
                    <tr key={i.id} className={suja ? 'selecionada' : undefined}>
                      <td>
                        <strong>{aluno?.nome_completo ?? `Aluno ${i.aluno_id}`}</strong>
                        <br />
                        <small className="cartao-sub">{aluno?.matricula}</small>
                        {erros[i.id] && (
                          <p className="erro-campo" role="alert">
                            {erros[i.id]}
                          </p>
                        )}
                      </td>
                      {PERIODOS.map((p) => {
                        const varias = nota(i.id, p).length > 1;
                        return (
                          <td key={`n-${p}`}>
                            <input
                              type="text"
                              inputMode="decimal"
                              className="celula"
                              aria-label={`Nota ${p} de ${aluno?.nome_completo ?? i.aluno_id}`}
                              value={varias ? '' : e[`nota_${p}`]}
                              placeholder={varias ? 'várias' : '—'}
                              disabled={varias}
                              title={varias ? 'Há mais de uma avaliação neste período; edite pela API.' : undefined}
                              onChange={(ev) => digitar(i.id, `nota_${p}`, ev.target.value)}
                            />
                          </td>
                        );
                      })}
                      {PERIODOS.map((p) => (
                        <td key={`f-${p}`}>
                          <input
                            type="number"
                            min="0"
                            step="1"
                            className="celula"
                            aria-label={`Faltas ${p} de ${aluno?.nome_completo ?? i.aluno_id}`}
                            value={e[`faltas_${p}`]}
                            placeholder="—"
                            onChange={(ev) => digitar(i.id, `faltas_${p}`, ev.target.value)}
                          />{' '}
                          <small className="cartao-sub">de {frequencia(i.id, p)?.aulas_previstas ?? aulas[p]}</small>
                        </td>
                      ))}
                      <td className="direita">
                        <button
                          type="button"
                          className="botao-primario botao-novo"
                          disabled={!suja || salvando}
                          onClick={() => salvar([i])}
                        >
                          <Save size={15} aria-hidden="true" /> Salvar
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="paginacao">
            <span className="cartao-sub">{sujas.length} linha(s) com alterações</span>
            <button type="button" disabled={sujas.length === 0 || salvando} onClick={() => salvar(sujas)}>
              {salvando ? 'Salvando…' : 'Salvar todas'}
            </button>
          </div>
        </>
      )}
    </>
  );
}
