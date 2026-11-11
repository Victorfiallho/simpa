import { Pencil, Plus, Search, UserMinus } from 'lucide-react';
import { type FormEvent, type ReactNode, useState } from 'react';

import { api } from '../api/cliente';
import type {
  AlunoCadastro,
  DisciplinaCadastro,
  InscricaoCadastro,
  Resposta,
  RespostaPaginada,
  TurmaCadastro,
} from '../api/tipos';
import { useDados } from '../api/useDados';
import { useNomesDeTurma } from '../api/useNomesDeTurma';
import { Conteudo } from '../componentes/Conteudo';
import { Gaveta } from '../componentes/Gaveta';
import { LegendaObrigatorios, Rotulo } from '../componentes/Obrigatorio';

// Cadastros do acadêmico (RF01, RF02) para admin e coordenação (D03). O professor não vê esta tela.

type Aba = 'turmas' | 'disciplinas' | 'alunos' | 'inscricoes';

const ABAS: { chave: Aba; rotulo: string }[] = [
  { chave: 'turmas', rotulo: 'Turmas' },
  { chave: 'disciplinas', rotulo: 'Disciplinas' },
  { chave: 'alunos', rotulo: 'Alunos' },
  { chave: 'inscricoes', rotulo: 'Inscrições' },
];

const POR_PAGINA = 15;

const ROTULO_STATUS: Record<string, string> = {
  ativa: 'Ativa',
  ativo: 'Ativo',
  inativa: 'Inativa',
  inativo: 'Inativo',
  encerrada: 'Encerrada',
  transferido: 'Transferido',
  concluido: 'Concluído',
  evadido: 'Evadido',
  concluida: 'Concluída',
  trancada: 'Trancada',
  cancelada: 'Cancelada',
};
const rotuloStatus = (s: string) => ROTULO_STATUS[s] ?? s;

const STATUS_TURMA = ['ativa', 'inativa', 'encerrada'];
// Iguais aos do backend (StatusAluno): tests/contrato confere.
const STATUS_ALUNO = ['ativo', 'inativo', 'transferido', 'concluido', 'evadido'];
const STATUS_INSCRICAO = ['ativa', 'trancada', 'concluida', 'cancelada'];
const TURNOS = ['matutino', 'vespertino', 'noturno', 'integral'];

interface Opcao {
  valor: string;
  rotulo: string;
}

interface Campo {
  chave: string;
  rotulo: string;
  tipo: 'texto' | 'email' | 'numero' | 'data' | 'opcoes';
  obrigatorio?: boolean;
  /** O campo só existe ao criar (o backend não aceita alterá-lo depois). */
  soNaCriacao?: boolean;
  dica?: string;
  maximo?: number;
  opcoes?: Opcao[];
  /** Nome a mostrar para o valor atual quando ele não está nas `opcoes` (lista cortada em 100). */
  rotuloDoValorAtual?: (valor: string) => string;
}

interface Coluna<T> {
  titulo: string;
  valor: (linha: T) => ReactNode;
}

interface Entidade<T extends { id: number; status: string }> {
  rota: string;
  singular: string;
  /** Concordância em português: "Nova turma", "Novo aluno". */
  feminino: boolean;
  colunas: Coluna<T>[];
  campos: Campo[];
  statusDisponiveis: string[];
  /** Valores iniciais do formulário de edição. */
  paraFormulario: (linha: T) => Record<string, string>;
  /** Texto que identifica a linha em mensagens de confirmação. */
  nome: (linha: T) => string;
  busca?: boolean;
}

const maiuscula = (t: string) => `${t[0].toUpperCase()}${t.slice(1)}`;
const novo = <T extends { id: number; status: string }>(e: Entidade<T>) => (e.feminino ? 'Nova' : 'Novo');
const sufixo = <T extends { id: number; status: string }>(e: Entidade<T>) => (e.feminino ? 'a' : 'o');

/**
 * Opções de um campo de escolha. O valor atual sempre entra, mesmo fora da lista (que vem cortada em
 * 100): sem isso o `select` ficaria vazio e o formulário de edição não poderia ser enviado.
 */
function opcoesDoCampo(campo: Campo, atual: string): Opcao[] {
  const opcoes = campo.opcoes ?? [];
  if (!atual || opcoes.some((o) => o.valor === atual)) return opcoes;
  return [{ valor: atual, rotulo: campo.rotuloDoValorAtual?.(atual) ?? atual }, ...opcoes];
}

/** Texto vazio vira null nos campos opcionais; número vira número. */
function converter(campo: Campo, texto: string): unknown {
  const limpo = texto.trim();
  if (limpo === '') return campo.obrigatorio ? '' : null;
  return campo.tipo === 'numero' ? Number(limpo) : limpo;
}

/** `aoMudarTurmas` avisa o app quando uma turma muda, para o filtro de turmas das outras telas se atualizar. */
export function Cadastros({ aoMudarTurmas }: { aoMudarTurmas?: () => void }) {
  const [aba, setAba] = useState<Aba>('turmas');
  const turmas = useDados(
    () =>
      api<RespostaPaginada<TurmaCadastro>>(
        // As mais recentes: são as que importam para novos cadastros. O nome das demais é buscado por id.
        '/academico/turmas?limite=100&ordenar_por=id&ordem=desc',
      ).then((r) => ({
        itens: [...r.dados].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
        total: r.total_registros,
      })),
    [],
  );
  const nomeTurma = useNomesDeTurma(turmas.dados?.itens ?? []);

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Cadastros</h2>
          <p className="cartao-sub">Turmas, disciplinas, alunos e inscrições do período.</p>
        </div>
      </div>
      <div className="ferramentas">
        <div className="segmentos" role="group" aria-label="Tipo de cadastro">
          {ABAS.map((a) => (
            <button key={a.chave} type="button" aria-pressed={aba === a.chave} onClick={() => setAba(a.chave)}>
              {a.rotulo}
            </button>
          ))}
        </div>
      </div>
      <Conteudo estado={turmas}>
        {({ itens: listaTurmas, total }) => {
          const opcoesTurma = listaTurmas.map((t) => ({ valor: String(t.id), rotulo: `${t.nome} · ${t.periodo_letivo}` }));
          // As listas de turma desta tela (e dos formulários) vêm limitadas a 100: avisa, em vez de
          // esconder as demais em silêncio.
          const aviso =
            total > listaTurmas.length ? (
              <p className="aviso" role="status">
                Nas listas de escolha aparecem as {listaTurmas.length} turmas mais recentes, de {total}.
              </p>
            ) : null;
          let painel;
          if (aba === 'turmas') {
            painel = (
              <PainelTurmas
                aoMudar={() => {
                  turmas.recarregar();
                  aoMudarTurmas?.();
                }}
              />
            );
          } else if (aba === 'disciplinas') {
            painel = <PainelDisciplinas nomeTurma={nomeTurma} opcoesTurma={opcoesTurma} />;
          } else if (aba === 'alunos') {
            painel = <PainelAlunos nomeTurma={nomeTurma} opcoesTurma={opcoesTurma} />;
          } else {
            painel = <PainelInscricoes turmas={listaTurmas} />;
          }
          return (
            <>
              {aviso}
              {painel}
            </>
          );
        }}
      </Conteudo>
    </section>
  );
}

// ---------- Turmas ----------

function PainelTurmas({ aoMudar }: { aoMudar: () => void }) {
  const entidade: Entidade<TurmaCadastro> = {
    rota: '/academico/turmas',
    singular: 'turma',
    feminino: true,
    statusDisponiveis: STATUS_TURMA,
    colunas: [
      { titulo: 'Código', valor: (t) => t.codigo ?? '—' },
      { titulo: 'Turma', valor: (t) => <strong>{t.nome}</strong> },
      { titulo: 'Curso', valor: (t) => t.curso },
      { titulo: 'Período', valor: (t) => t.periodo_letivo },
      { titulo: 'Turno', valor: (t) => t.turno },
      { titulo: 'Sala', valor: (t) => t.sala ?? '—' },
    ],
    campos: [
      { chave: 'nome', rotulo: 'Nome da turma', tipo: 'texto', obrigatorio: true, maximo: 120 },
      { chave: 'codigo', rotulo: 'Código (opcional)', tipo: 'texto', maximo: 20 },
      { chave: 'curso', rotulo: 'Curso', tipo: 'texto', obrigatorio: true, maximo: 120 },
      { chave: 'periodo_letivo', rotulo: 'Período letivo', tipo: 'texto', obrigatorio: true, dica: 'Ex.: 2026.2' },
      {
        chave: 'turno',
        rotulo: 'Turno',
        tipo: 'opcoes',
        obrigatorio: true,
        opcoes: TURNOS.map((t) => ({ valor: t, rotulo: t })),
      },
      { chave: 'sala', rotulo: 'Sala (opcional)', tipo: 'texto', maximo: 20 },
    ],
    paraFormulario: (t) => ({
      nome: t.nome,
      codigo: t.codigo ?? '',
      curso: t.curso,
      periodo_letivo: t.periodo_letivo,
      turno: t.turno,
      sala: t.sala ?? '',
    }),
    nome: (t) => t.nome,
  };
  return <PainelEntidade entidade={entidade} aoMudar={aoMudar} />;
}

// ---------- Disciplinas ----------

function PainelDisciplinas({
  nomeTurma,
  opcoesTurma,
}: {
  nomeTurma: (id: number) => string;
  opcoesTurma: Opcao[];
}) {
  // Professores para escolher o responsável pelo nome. Se a lista não carregar (ou o professor for
  // inativo/além dos 100), a tela mostra "Usuário N" em vez de esconder o vínculo.
  const professores = useDados(
    () =>
      api<RespostaPaginada<{ id: number; nome_usuario: string }>>(
        '/auth/usuarios?role=professor&ativo=true&limite=100',
      ).then((r) => r.dados),
    [],
  );
  const nomesDeProfessor = new Map((professores.dados ?? []).map((u) => [u.id, u.nome_usuario]));
  const nomeProfessor = (id: number) => nomesDeProfessor.get(id) ?? `Usuário ${id}`;
  const opcoesProfessor: Opcao[] = (professores.dados ?? []).map((u) => ({
    valor: String(u.id),
    rotulo: u.nome_usuario,
  }));
  const entidade: Entidade<DisciplinaCadastro> = {
    rota: '/academico/disciplinas',
    singular: 'disciplina',
    feminino: true,
    statusDisponiveis: STATUS_TURMA,
    colunas: [
      { titulo: 'Código', valor: (d) => d.codigo ?? '—' },
      { titulo: 'Disciplina', valor: (d) => <strong>{d.nome}</strong> },
      { titulo: 'Turma', valor: (d) => nomeTurma(d.turma_id) },
      { titulo: 'Período', valor: (d) => d.periodo_letivo },
      { titulo: 'Carga', valor: (d) => `${d.carga_horaria} h` },
      { titulo: 'Professor', valor: (d) => (d.professor_id ? nomeProfessor(d.professor_id) : '—') },
    ],
    campos: [
      { chave: 'nome', rotulo: 'Nome da disciplina', tipo: 'texto', obrigatorio: true, maximo: 120 },
      { chave: 'codigo', rotulo: 'Código (opcional)', tipo: 'texto', maximo: 20 },
      {
        chave: 'turma_id',
        rotulo: 'Turma',
        tipo: 'opcoes',
        obrigatorio: true,
        soNaCriacao: true,
        opcoes: opcoesTurma,
      },
      { chave: 'periodo_letivo', rotulo: 'Período letivo', tipo: 'texto', obrigatorio: true, dica: 'Ex.: 2026.2' },
      { chave: 'carga_horaria', rotulo: 'Carga horária (horas)', tipo: 'numero', obrigatorio: true },
      {
        chave: 'professor_id',
        rotulo: 'Professor responsável (opcional)',
        tipo: 'opcoes',
        opcoes: opcoesProfessor,
        rotuloDoValorAtual: (valor) => nomeProfessor(Number(valor)),
      },
    ],
    paraFormulario: (d) => ({
      nome: d.nome,
      codigo: d.codigo ?? '',
      turma_id: String(d.turma_id),
      periodo_letivo: d.periodo_letivo,
      carga_horaria: String(d.carga_horaria),
      professor_id: d.professor_id ? String(d.professor_id) : '',
    }),
    nome: (d) => d.nome,
  };
  return <PainelEntidade entidade={entidade} />;
}

// ---------- Alunos ----------

function PainelAlunos({
  nomeTurma,
  opcoesTurma,
}: {
  nomeTurma: (id: number) => string;
  opcoesTurma: Opcao[];
}) {
  const entidade: Entidade<AlunoCadastro> = {
    rota: '/academico/alunos',
    singular: 'aluno',
    feminino: false,
    statusDisponiveis: STATUS_ALUNO,
    busca: true,
    colunas: [
      { titulo: 'Matrícula', valor: (a) => a.matricula },
      { titulo: 'Aluno', valor: (a) => <strong>{a.nome_completo}</strong> },
      { titulo: 'E-mail', valor: (a) => a.email },
      { titulo: 'Turma', valor: (a) => nomeTurma(a.turma_id) },
    ],
    campos: [
      {
        chave: 'matricula',
        rotulo: 'Matrícula',
        tipo: 'texto',
        obrigatorio: true,
        soNaCriacao: true,
        dica: 'De 4 a 20 dígitos.',
      },
      { chave: 'nome_completo', rotulo: 'Nome completo', tipo: 'texto', obrigatorio: true, maximo: 150 },
      { chave: 'email', rotulo: 'E-mail', tipo: 'email', obrigatorio: true },
      {
        chave: 'cpf',
        rotulo: 'CPF (opcional)',
        tipo: 'texto',
        dica: 'Por privacidade o CPF nunca é mostrado de volta. Deixe vazio para manter o atual.',
      },
      { chave: 'telefone', rotulo: 'Telefone (opcional)', tipo: 'texto', maximo: 20 },
      { chave: 'data_nascimento', rotulo: 'Data de nascimento (opcional)', tipo: 'data' },
      { chave: 'curso', rotulo: 'Curso', tipo: 'texto', obrigatorio: true, maximo: 120 },
      {
        chave: 'turma_id',
        rotulo: 'Turma',
        tipo: 'opcoes',
        obrigatorio: true,
        opcoes: opcoesTurma,
        rotuloDoValorAtual: (valor) => nomeTurma(Number(valor)),
      },
    ],
    paraFormulario: (a) => ({
      nome_completo: a.nome_completo,
      email: a.email,
      cpf: '',
      telefone: a.telefone ?? '',
      data_nascimento: a.data_nascimento ?? '',
      curso: a.curso,
      turma_id: String(a.turma_id),
    }),
    nome: (a) => a.nome_completo,
  };
  return <PainelEntidade entidade={entidade} />;
}

// ---------- Lista + formulário genéricos ----------

function PainelEntidade<T extends { id: number; status: string }>({
  entidade,
  aoMudar,
}: {
  entidade: Entidade<T>;
  aoMudar?: () => void;
}) {
  const [pagina, setPagina] = useState(1);
  const [status, setStatus] = useState('');
  const [busca, setBusca] = useState('');
  const [formulario, setFormulario] = useState<{ linha: T | null } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const consulta = new URLSearchParams({ pagina: String(pagina), limite: String(POR_PAGINA), ordenar_por: 'id', ordem: 'desc' });
  if (status) consulta.set('status', status);
  if (busca.trim().length >= 2) consulta.set('busca', busca.trim());
  const lista = useDados(
    () => api<RespostaPaginada<T>>(`${entidade.rota}?${consulta}`),
    [entidade.rota, consulta.toString()],
  );

  function filtrar(mudar: () => void) {
    mudar();
    setPagina(1);
  }

  async function inativar(linha: T) {
    if (!window.confirm(`Inativar ${entidade.singular} "${entidade.nome(linha)}"? O histórico é mantido.`)) return;
    setErro(null);
    setAviso(null);
    try {
      await api(`${entidade.rota}/${linha.id}`, { method: 'DELETE' });
      setAviso(`${maiuscula(entidade.singular)} inativad${sufixo(entidade)}.`);
      lista.recarregar();
      aoMudar?.();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  function salvou(texto: string) {
    setFormulario(null);
    setAviso(texto);
    lista.recarregar();
    aoMudar?.();
  }

  return (
    <>
      <div className="ferramentas">
        {entidade.busca && (
          <label className="busca">
            <Search size={16} aria-hidden="true" />
            <input
              type="search"
              placeholder="Buscar por nome ou matrícula"
              aria-label="Buscar por nome ou matrícula"
              value={busca}
              onChange={(e) => filtrar(() => setBusca(e.target.value))}
            />
          </label>
        )}
        <label className="campo-linha">
          Situação
          <select value={status} onChange={(e) => filtrar(() => setStatus(e.target.value))}>
            <option value="">Todas</option>
            {entidade.statusDisponiveis.map((s) => (
              <option key={s} value={s}>
                {rotuloStatus(s)}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="botao-primario botao-novo" onClick={() => setFormulario({ linha: null })}>
          <Plus size={16} aria-hidden="true" /> {novo(entidade)} {entidade.singular}
        </button>
      </div>
      {aviso && (
        <p className="aviso-sucesso" role="status">
          {aviso}
        </p>
      )}
      {erro && (
        <p className="erro-campo" role="alert">
          {erro}
        </p>
      )}
      <Conteudo estado={lista}>
        {(resposta) => (
          <ListaTabela
            entidade={entidade}
            resposta={resposta}
            pagina={pagina}
            aoPaginar={setPagina}
            aoEditar={(linha) => setFormulario({ linha })}
            aoInativar={inativar}
          />
        )}
      </Conteudo>
      {formulario && (
        <FormularioEntidade
          entidade={entidade}
          linha={formulario.linha}
          aoFechar={() => setFormulario(null)}
          aoSalvar={salvou}
        />
      )}
    </>
  );
}

function ListaTabela<T extends { id: number; status: string }>({
  entidade,
  resposta,
  pagina,
  aoPaginar,
  aoEditar,
  aoInativar,
}: {
  entidade: Entidade<T>;
  resposta: RespostaPaginada<T>;
  pagina: number;
  aoPaginar: (p: number) => void;
  aoEditar: (linha: T) => void;
  aoInativar: (linha: T) => void;
}) {
  const paginas = Math.max(1, Math.ceil(resposta.total_registros / resposta.limite));
  if (resposta.dados.length === 0) {
    return <p className="vazio">Nenhum registro neste recorte.</p>;
  }
  return (
    <>
      <div className="tabela-rolagem">
        <table className="tabela">
          <thead>
            <tr>
              {entidade.colunas.map((c) => (
                <th key={c.titulo}>{c.titulo}</th>
              ))}
              <th>Situação</th>
              <th className="direita">Ações</th>
            </tr>
          </thead>
          <tbody>
            {resposta.dados.map((linha) => {
              const inativa = !['ativa', 'ativo'].includes(linha.status);
              return (
                <tr key={linha.id} className={inativa ? 'encerrado' : undefined}>
                  {entidade.colunas.map((c) => (
                    <td key={c.titulo}>{c.valor(linha)}</td>
                  ))}
                  <td>{rotuloStatus(linha.status)}</td>
                  <td className="direita acoes">
                    <button
                      type="button"
                      className="botao-icone"
                      aria-label={`Editar ${entidade.nome(linha)}`}
                      onClick={() => aoEditar(linha)}
                    >
                      <Pencil size={15} />
                    </button>
                    {!inativa && (
                      <button
                        type="button"
                        className="botao-icone"
                        aria-label={`Inativar ${entidade.nome(linha)}`}
                        onClick={() => aoInativar(linha)}
                      >
                        <UserMinus size={15} />
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="paginacao">
        <span className="cartao-sub">
          {resposta.total_registros} registro(s) · página {pagina} de {paginas}
        </span>
        <button type="button" disabled={pagina <= 1} onClick={() => aoPaginar(pagina - 1)}>
          Anterior
        </button>
        <button type="button" disabled={pagina >= paginas} onClick={() => aoPaginar(pagina + 1)}>
          Próxima
        </button>
      </div>
    </>
  );
}

function FormularioEntidade<T extends { id: number; status: string }>({
  entidade,
  linha,
  aoFechar,
  aoSalvar,
}: {
  entidade: Entidade<T>;
  linha: T | null;
  aoFechar: () => void;
  aoSalvar: (texto: string) => void;
}) {
  const editando = linha !== null;
  const inicial = linha ? entidade.paraFormulario(linha) : {};
  const campos = entidade.campos.filter((c) => !(editando && c.soNaCriacao));
  const [valores, setValores] = useState<Record<string, string>>(() =>
    Object.fromEntries(campos.map((c) => [c.chave, inicial[c.chave] ?? ''])),
  );
  const [situacao, setSituacao] = useState(linha?.status ?? '');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      if (editando) {
        // Só vai o que mudou: o que não foi tocado (como o CPF, que nunca volta do servidor) fica como está.
        const corpo: Record<string, unknown> = {};
        for (const c of campos) {
          if (valores[c.chave] !== (inicial[c.chave] ?? '')) corpo[c.chave] = converter(c, valores[c.chave]);
        }
        if (situacao !== linha.status) corpo.status = situacao;
        if (Object.keys(corpo).length === 0) {
          aoFechar();
          return;
        }
        await api(`${entidade.rota}/${linha.id}`, { method: 'PATCH', body: JSON.stringify(corpo) });
        aoSalvar('Alterações salvas.');
      } else {
        const corpo = Object.fromEntries(campos.map((c) => [c.chave, converter(c, valores[c.chave])]));
        await api<Resposta<T>>(entidade.rota, { method: 'POST', body: JSON.stringify(corpo) });
        aoSalvar(`${maiuscula(entidade.singular)} cadastrad${sufixo(entidade)}.`);
      }
    } catch (err) {
      setErro((err as Error).message);
      setEnviando(false);
    }
  }

  return (
    <Gaveta
      titulo={editando ? `Editar ${entidade.singular}` : `${novo(entidade)} ${entidade.singular}`}
      subtitulo={editando ? entidade.nome(linha) : undefined}
      aoFechar={aoFechar}
    >
      <form className="coluna" onSubmit={enviar}>
        {campos.some((c) => c.obrigatorio) && <LegendaObrigatorios />}
        {campos.map((c) => (
          <label className="campo" key={c.chave}>
            <Rotulo texto={c.rotulo} obrigatorio={c.obrigatorio} />
            {c.tipo === 'opcoes' ? (
              <select
                value={valores[c.chave]}
                required={c.obrigatorio}
                onChange={(e) => setValores({ ...valores, [c.chave]: e.target.value })}
              >
                <option value="">Selecione…</option>
                {opcoesDoCampo(c, valores[c.chave]).map((o) => (
                  <option key={o.valor} value={o.valor}>
                    {o.rotulo}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={c.tipo === 'texto' ? 'text' : c.tipo === 'numero' ? 'number' : c.tipo}
                value={valores[c.chave]}
                required={c.obrigatorio}
                maxLength={c.maximo}
                min={c.tipo === 'numero' ? 1 : undefined}
                onChange={(e) => setValores({ ...valores, [c.chave]: e.target.value })}
              />
            )}
            {c.dica && <small className="cartao-sub">{c.dica}</small>}
          </label>
        ))}
        {editando && (
          <label className="campo">
            Situação
            <select value={situacao} onChange={(e) => setSituacao(e.target.value)}>
              {entidade.statusDisponiveis.map((s) => (
                <option key={s} value={s}>
                  {rotuloStatus(s)}
                </option>
              ))}
            </select>
          </label>
        )}
        {erro && (
          <p className="erro-campo" role="alert">
            {erro}
          </p>
        )}
        <button type="submit" className="botao-primario" disabled={enviando}>
          {enviando ? 'Salvando…' : editando ? 'Salvar alterações' : 'Cadastrar'}
        </button>
      </form>
    </Gaveta>
  );
}

// ---------- Inscrições ----------

function PainelInscricoes({ turmas }: { turmas: TurmaCadastro[] }) {
  const [disciplinaId, setDisciplinaId] = useState('');
  const [matricula, setMatricula] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const disciplinas = useDados(
    () =>
      api<RespostaPaginada<DisciplinaCadastro>>(
        '/academico/disciplinas?limite=100&status=ativa&ordenar_por=nome',
      ).then((r) => ({ itens: r.dados, total: r.total_registros })),
    [],
  );
  const disciplina = disciplinas.dados?.itens.find((d) => String(d.id) === disciplinaId) ?? null;

  const inscricoes = useDados(
    () =>
      disciplina
        ? Promise.all([
            api<RespostaPaginada<InscricaoCadastro>>(
              `/academico/inscricoes?disciplina_id=${disciplina.id}&limite=100&ordenar_por=id`,
            ),
            api<RespostaPaginada<AlunoCadastro>>(
              `/academico/alunos?turma_id=${disciplina.turma_id}&limite=100&ordenar_por=nome_completo`,
            ),
          ]).then(([i, a]) => ({ inscricoes: i.dados, alunos: a.dados }))
        : Promise.resolve({ inscricoes: [] as InscricaoCadastro[], alunos: [] as AlunoCadastro[] }),
    [disciplinaId],
  );

  async function inscrever(e: FormEvent) {
    e.preventDefault();
    if (!disciplina) return;
    setEnviando(true);
    setErro(null);
    setAviso(null);
    try {
      // A matrícula é o que a secretaria tem em mãos; o id do aluno vem da consulta por matrícula (RF04).
      const aluno = await api<Resposta<AlunoCadastro>>(
        `/academico/alunos/matricula/${encodeURIComponent(matricula.trim())}`,
      );
      await api('/academico/inscricoes', {
        method: 'POST',
        body: JSON.stringify({ aluno_id: aluno.dados.id, disciplina_id: disciplina.id }),
      });
      setAviso(`${aluno.dados.nome_completo} inscrito(a) em ${disciplina.nome}.`);
      setMatricula('');
      inscricoes.recarregar();
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  async function mudarStatus(inscricao: InscricaoCadastro, status: string) {
    setErro(null);
    setAviso(null);
    try {
      await api(`/academico/inscricoes/${inscricao.id}`, { method: 'PATCH', body: JSON.stringify({ status }) });
      inscricoes.recarregar();
    } catch (err) {
      setErro((err as Error).message);
    }
  }

  const nomeTurma = useNomesDeTurma(turmas);

  return (
    <>
      <div className="ferramentas">
        <label className="campo-linha">
          Disciplina
          <select value={disciplinaId} onChange={(e) => setDisciplinaId(e.target.value)}>
            <option value="">Selecione…</option>
            {(disciplinas.dados?.itens ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome} · {nomeTurma(d.turma_id)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {disciplinas.dados && disciplinas.dados.total > disciplinas.dados.itens.length && (
        <p className="aviso" role="status">
          Mostrando as primeiras {disciplinas.dados.itens.length} de {disciplinas.dados.total} disciplinas ativas.
        </p>
      )}
      {disciplina && (
        <form className="parametros" onSubmit={inscrever}>
          <label className="campo">
            <Rotulo texto="Matrícula do aluno" obrigatorio />
            <input
              type="text"
              value={matricula}
              required
              inputMode="numeric"
              onChange={(e) => setMatricula(e.target.value)}
            />
          </label>
          <button type="submit" className="botao-primario botao-novo" disabled={enviando}>
            <Plus size={16} aria-hidden="true" /> {enviando ? 'Inscrevendo…' : 'Inscrever'}
          </button>
        </form>
      )}
      {aviso && (
        <p className="aviso-sucesso" role="status">
          {aviso}
        </p>
      )}
      {erro && (
        <p className="erro-campo" role="alert">
          {erro}
        </p>
      )}
      {!disciplina ? (
        <p className="vazio">Escolha uma disciplina para ver e gerenciar as inscrições.</p>
      ) : (
        <Conteudo estado={inscricoes}>
          {({ inscricoes: itens, alunos }) =>
            itens.length === 0 ? (
              <p className="vazio">Nenhum aluno inscrito nesta disciplina ainda.</p>
            ) : (
              <div className="tabela-rolagem">
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Matrícula</th>
                      <th>Aluno</th>
                      <th>Situação da inscrição</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itens.map((i) => {
                      const aluno = alunos.find((a) => a.id === i.aluno_id);
                      return (
                        <tr key={i.id} className={i.status !== 'ativa' ? 'encerrado' : undefined}>
                          <td>{aluno?.matricula ?? '—'}</td>
                          <td>
                            <strong>{aluno?.nome_completo ?? `Aluno ${i.aluno_id}`}</strong>
                          </td>
                          <td>
                            <select
                              value={i.status}
                              aria-label={`Situação da inscrição de ${aluno?.nome_completo ?? i.aluno_id}`}
                              onChange={(e) => mudarStatus(i, e.target.value)}
                            >
                              {STATUS_INSCRICAO.map((s) => (
                                <option key={s} value={s}>
                                  {rotuloStatus(s)}
                                </option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          }
        </Conteudo>
      )}
    </>
  );
}
