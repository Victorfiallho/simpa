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

export function Marca({ tamanho = 34 }: { tamanho?: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 32 32" aria-hidden="true">
      <rect x="4" y="7" width="22" height="5" rx="2.5" fill="#ea7957" />
      <rect x="4" y="14" width="15" height="5" rx="2.5" fill="#e1ba58" />
      <rect x="4" y="21" width="19" height="5" rx="2.5" fill="#8ca573" />
    </svg>
  );
}

export function BarraLateral() {
  const { usuario, sair } = useSessao();

  return (
    <aside className="barra">
      <NavLink to="/" className="marca" aria-label="SIMPA, ir para a visão geral">
        <Marca />
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
