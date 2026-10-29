import { ChartColumn, FileText, LayoutDashboard, LogOut, Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import { iniciais } from '../dados/formato';
import { useSessao } from '../sessao';

const ITENS = [
  { para: '/', rotulo: 'Visão geral', Icone: LayoutDashboard },
  { para: '/alunos', rotulo: 'Alunos', Icone: Users },
  { para: '/analises', rotulo: 'Análises', Icone: ChartColumn },
  { para: '/relatorios', rotulo: 'Relatórios', Icone: FileText },
];

const PERFIL = { admin: 'Administração', coordenador: 'Coordenação', professor: 'Professor' };

/** Símbolo da logo (as três faixas), para fundos escuros e espaços pequenos. */
function Simbolo() {
  return <img src="/simbolo.png" alt="" width={40} height={34} />;
}

export function BarraLateral() {
  const { usuario, sair } = useSessao();

  return (
    <aside className="barra">
      <NavLink to="/" className="marca" aria-label="SIMPA, ir para a visão geral">
        <Simbolo />
        <span>SIMPA</span>
      </NavLink>

      <nav aria-label="Menu principal">
        {ITENS.map(({ para, rotulo, Icone }) => (
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
