import {
  BellRing,
  Bot,
  ChartColumn,
  FileText,
  LayoutDashboard,
  LogOut,
  ScrollText,
  SlidersHorizontal,
  Users,
} from 'lucide-react';
import { NavLink } from 'react-router-dom';

import { iniciais } from '../dados/formato';
import { useSessao } from '../sessao';

const ITENS = [
  { para: '/', rotulo: 'Visão geral', Icone: LayoutDashboard },
  { para: '/alunos', rotulo: 'Alunos', Icone: Users },
  { para: '/analises', rotulo: 'Análises', Icone: ChartColumn },
  { para: '/relatorios', rotulo: 'Relatórios', Icone: FileText },
];

// Só para admin e coordenador (D03): alertas, simulações, copiloto e trilha de auditoria.
const ITENS_DA_GESTAO = [
  { para: '/alertas', rotulo: 'Alertas', Icone: BellRing },
  { para: '/cenarios', rotulo: 'Cenários', Icone: SlidersHorizontal },
  { para: '/copiloto', rotulo: 'Copiloto', Icone: Bot },
  { para: '/auditoria', rotulo: 'Auditoria', Icone: ScrollText },
];

const PERFIL = { admin: 'Administração', coordenador: 'Coordenação', professor: 'Professor' };

/** Símbolo da logo (as três faixas), para fundos escuros e espaços pequenos. */
function Simbolo() {
  return <img src="/simbolo.png" alt="" width={40} height={34} />;
}

export function BarraLateral() {
  const { usuario, sair } = useSessao();
  const gestao = usuario?.role === 'admin' || usuario?.role === 'coordenador';
  const itens = gestao ? [...ITENS, ...ITENS_DA_GESTAO] : ITENS;

  return (
    <aside className="barra">
      <NavLink to="/" className="marca" aria-label="SIMPA, ir para a visão geral">
        <Simbolo />
        <span>SIMPA</span>
      </NavLink>

      <nav aria-label="Menu principal">
        {itens.map(({ para, rotulo, Icone }) => (
          <NavLink key={para} to={para} end={para === '/'}>
            <span className="icone">
              <Icone size={19} strokeWidth={1.8} />
            </span>
            {rotulo}
          </NavLink>
        ))}
      </nav>

      {usuario && (
        <div className="perfil">
          <span className="avatar" title={usuario.nome_usuario}>
            {iniciais(usuario.nome_usuario.replace('.', ' '))}
          </span>
          {PERFIL[usuario.role]}
          <button type="button" className="sair" onClick={sair}>
            <LogOut size={14} aria-hidden="true" /> Sair
          </button>
        </div>
      )}
    </aside>
  );
}
