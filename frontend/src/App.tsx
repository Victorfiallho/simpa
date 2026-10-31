import { type ReactNode, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { api } from './api/cliente';
import type { Painel, Resposta, RespostaPaginada, Turma } from './api/tipos';
import { useDados } from './api/useDados';
import { BarraLateral } from './componentes/BarraLateral';
import { Cabecalho, type Filtros } from './componentes/Cabecalho';
import { Conteudo } from './componentes/Conteudo';
import { Alertas } from './paginas/Alertas';
import { Alunos } from './paginas/Alunos';
import { Analises } from './paginas/Analises';
import { Auditoria } from './paginas/Auditoria';
import { Cenarios } from './paginas/Cenarios';
import { Copiloto } from './paginas/Copiloto';
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
      <main className="painel">{conteudo}</main>
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

  // Cada tela nova começa do topo.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  const turmas = useDados(
    () =>
      api<RespostaPaginada<Turma>>('/academico/turmas?limite=100&ordenar_por=nome').then(
        (r) => r.dados,
      ),
    [],
  );

  const consulta = new URLSearchParams();
  if (filtros.turmaId) consulta.set('turma_id', String(filtros.turmaId));
  if (filtros.periodo) consulta.set('periodo_letivo', filtros.periodo);
  const painel = useDados(
    () => api<Resposta<Painel>>(`/analitico/painel?${consulta}`).then((r) => r.dados),
    [consulta.toString()],
  );

  const listaDeTurmas = turmas.dados ?? [];
  const periodoMaisRecente = [...listaDeTurmas.map((t) => t.periodo_letivo)].sort().at(-1) ?? null;

  const pagina = (titulo: string, conteudo: ReactNode) => (
    <>
      <Cabecalho titulo={titulo} turmas={listaDeTurmas} filtros={filtros} aoMudar={setFiltros} />
      <main className="painel">{conteudo}</main>
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
