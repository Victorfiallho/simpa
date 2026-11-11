import { type ReactNode, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { api } from './api/cliente';
import type { Painel, Resposta, RespostaPaginada, Turma } from './api/tipos';
import { useDados } from './api/useDados';
import { BarraLateral } from './componentes/BarraLateral';
import { Transicao } from './componentes/Transicao';
import { Cabecalho, type Filtros } from './componentes/Cabecalho';
import { Conteudo } from './componentes/Conteudo';
import { Alertas } from './paginas/Alertas';
import { Alunos } from './paginas/Alunos';
import { Analises } from './paginas/Analises';
import { Auditoria } from './paginas/Auditoria';
import { Cadastros } from './paginas/Cadastros';
import { Cenarios } from './paginas/Cenarios';
import { Copiloto } from './paginas/Copiloto';
import { Lancamentos } from './paginas/Lancamentos';
import { Login } from './paginas/Login';
import { MeuApoio } from './paginas/MeuApoio';
import { MeuDesempenho } from './paginas/MeuDesempenho';
import { MeuPerfil } from './paginas/MeuPerfil';
import { Pendencias } from './paginas/Pendencias';
import { Relatorios } from './paginas/Relatorios';
import { VisaoGeral } from './paginas/VisaoGeral';
import { useSessao } from './sessao';

export function App() {
  const { usuario } = useSessao();
  if (!usuario) return <Login />;
  return usuario.role === 'aluno' ? <AplicacaoDoAluno /> : <Aplicacao />;
}

/** A API entrega no máximo 100 turmas por página; o filtro busca as páginas seguintes. */
const LIMITE_DE_PAGINAS = 20;

async function buscarTodasAsTurmas(): Promise<{ lista: Turma[]; omitidas: number }> {
  const lista: Turma[] = [];
  let total = 0;
  for (let pagina = 1; pagina <= LIMITE_DE_PAGINAS; pagina += 1) {
    const r = await api<RespostaPaginada<Turma>>(
      `/academico/turmas?limite=100&pagina=${pagina}&ordenar_por=nome`,
    );
    lista.push(...r.dados);
    total = r.total_registros;
    if (lista.length >= total || r.dados.length === 0) break;
  }
  // Só sobra algo omitido se passar do limite de páginas: o cabeçalho avisa em vez de esconder.
  return { lista, omitidas: Math.max(0, total - lista.length) };
}

/** O aluno só vê o que é dele: não busca turmas nem painel geral (o servidor recusaria). */
function AplicacaoDoAluno() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  const pagina = (titulo: string, conteudo: ReactNode) => (
    <>
      <header className="cabecalho">
        <h1>{titulo}</h1>
      </header>
      <main className="painel">
        <Transicao>{conteudo}</Transicao>
      </main>
    </>
  );

  return (
    <div className="app">
      <BarraLateral />
      <div className="area">
        <Routes>
          <Route path="/" element={pagina('Meu desempenho', <MeuDesempenho />)} />
          <Route path="/apoio" element={pagina('Pedir apoio', <MeuApoio />)} />
          <Route path="/perfil" element={pagina('Meu perfil', <MeuPerfil />)} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}

function Aplicacao() {
  const [filtros, setFiltros] = useState<Filtros>({ periodo: null, turmaId: null });
  const { pathname } = useLocation();
  const { usuario } = useSessao();

  // Cada tela nova começa do topo.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  const turmas = useDados(buscarTodasAsTurmas, []);

  const consulta = new URLSearchParams();
  if (filtros.turmaId) consulta.set('turma_id', String(filtros.turmaId));
  if (filtros.periodo) consulta.set('periodo_letivo', filtros.periodo);
  const painel = useDados(
    () => api<Resposta<Painel>>(`/analitico/painel?${consulta}`).then((r) => r.dados),
    [consulta.toString()],
  );

  const listaDeTurmas = turmas.dados?.lista ?? [];
  const turmasOmitidas = turmas.dados?.omitidas ?? 0;
  const periodoMaisRecente = [...listaDeTurmas.map((t) => t.periodo_letivo)].sort().at(-1) ?? null;

  const pagina = (titulo: string, conteudo: ReactNode) => (
    <>
      <Cabecalho
        titulo={titulo}
        turmas={listaDeTurmas}
        turmasOmitidas={turmasOmitidas}
        filtros={filtros}
        aoMudar={setFiltros}
      />
      <main className="painel">
        <Transicao>{conteudo}</Transicao>
      </main>
    </>
  );

  // Cadastros e lançamentos não usam os filtros de período e turma: o cabeçalho vai sem eles.
  const paginaSemFiltros = (titulo: string, conteudo: ReactNode) => (
    <>
      <header className="cabecalho">
        <h1>{titulo}</h1>
      </header>
      <main className="painel">
        <Transicao>{conteudo}</Transicao>
      </main>
    </>
  );

  return (
    <div className="app">
      <BarraLateral />
      <div className="area">
        <Routes>
          <Route
            path="/"
            element={pagina(
              'Visão geral',
              <Conteudo estado={painel}>{(dados) => <VisaoGeral painel={dados} />}</Conteudo>,
            )}
          />
          <Route
            path="/alunos"
            element={pagina(
              'Alunos',
              <Conteudo estado={painel}>{(dados) => <Alunos painel={dados} />}</Conteudo>,
            )}
          />
          <Route
            path="/analises"
            element={pagina(
              'Análises',
              <Analises turmaId={filtros.turmaId} periodo={filtros.periodo ?? periodoMaisRecente} />,
            )}
          />
          <Route
            path="/alertas"
            element={pagina(
              'Alertas',
              <Alertas turmaId={filtros.turmaId} periodo={filtros.periodo} />,
            )}
          />
          <Route
            path="/cenarios"
            element={pagina(
              'Cenários',
              <Cenarios turmaId={filtros.turmaId} periodo={filtros.periodo} />,
            )}
          />
          {(usuario?.role === 'admin' || usuario?.role === 'coordenador') && (
            <Route path="/cadastros" element={paginaSemFiltros('Cadastros', <Cadastros aoMudarTurmas={turmas.recarregar} />)} />
          )}
          {(usuario?.role === 'admin' || usuario?.role === 'professor') && (
            <Route path="/lancamentos" element={paginaSemFiltros('Lançamentos', <Lancamentos />)} />
          )}
          <Route path="/copiloto" element={pagina('Copiloto', <Copiloto />)} />
          <Route path="/pendencias" element={pagina('Pendências', <Pendencias />)} />
          <Route path="/auditoria" element={pagina('Auditoria', <Auditoria />)} />
          <Route path="/perfil" element={pagina('Meu perfil', <MeuPerfil />)} />
          <Route
            path="/relatorios"
            element={pagina(
              'Relatórios',
              <Conteudo estado={painel}>
                {(dados) => (
                  <Relatorios painel={dados} turmaId={filtros.turmaId} periodo={filtros.periodo} />
                )}
              </Conteudo>,
            )}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}
