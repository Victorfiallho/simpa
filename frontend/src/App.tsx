import { ChartColumn, FileText } from 'lucide-react';
import { type ReactNode, useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { BarraLateral } from './componentes/BarraLateral';
import { Cabecalho } from './componentes/Cabecalho';
import { gerarBaseDemonstracao } from './dados/demonstracao';
import { type FiltroTurma, montarPainel } from './dados/painel';
import { Alunos } from './paginas/Alunos';
import { EmBreve } from './paginas/EmBreve';
import { VisaoGeral } from './paginas/VisaoGeral';

// Enquanto a API do serviço analítico não existe, as telas usam a base de demonstração.
const base = gerarBaseDemonstracao();

export function App() {
  const [turma, setTurma] = useState<FiltroTurma>('todas');
  const painel = useMemo(() => montarPainel(base, turma), [turma]);
  const { pathname } = useLocation();

  // Cada tela nova começa do topo.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  const pagina = (titulo: string, conteudo: ReactNode) => (
    <>
      <Cabecalho
        titulo={titulo}
        periodo={painel.periodoLetivo}
        turma={turma}
        aoMudarTurma={setTurma}
      />
      <main className="painel">{conteudo}</main>
    </>
  );

  return (
    <div className="app">
      <BarraLateral />
      <div className="area">
        <Routes>
          <Route path="/" element={pagina('Visão geral', <VisaoGeral painel={painel} />)} />
          <Route path="/alunos" element={pagina('Alunos', <Alunos painel={painel} />)} />
          <Route
            path="/analises"
            element={pagina(
              'Análises',
              <EmBreve
                icone={<ChartColumn size={26} />}
                titulo="Análises estatísticas"
                descricao="Dispersão frequência × média, correlação e indicadores por período entram na Fase 2, junto com a API de indicadores do serviço analítico."
              />,
            )}
          />
          <Route
            path="/relatorios"
            element={pagina(
              'Relatórios',
              <EmBreve
                icone={<FileText size={26} />}
                titulo="Relatórios"
                descricao="Exportação em CSV, XLSX e PDF com os filtros aplicados entra na Fase 2 (RF11)."
              />,
            )}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}
