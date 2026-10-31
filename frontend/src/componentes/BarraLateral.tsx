import {
  BellRing,
  Bot,
  ChartColumn,
  FileText,
  Inbox,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  ScrollText,
  SlidersHorizontal,
  UserRound,
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
  { para: '/pendencias', rotulo: 'Pendências', Icone: Inbox },
  { para: '/auditoria', rotulo: 'Auditoria', Icone: ScrollText },
];

const ITEM_PERFIL = { para: '/perfil', rotulo: 'Meu perfil', Icone: UserRound };

// O aluno só tem as telas dele.
const ITENS_DO_ALUNO = [
  { para: '/', rotulo: 'Meu desempenho', Icone: LayoutDashboard },
  { para: '/apoio', rotulo: 'Pedir apoio', Icone: LifeBuoy },
  ITEM_PERFIL,
];

const PERFIL = {
  admin: 'Administração',
  coordenador: 'Coordenação',
  professor: 'Professor',
  aluno: 'Aluno',
};

/** Símbolo da logo (as três faixas), para fundos escuros e espaços pequenos. */
function Simbolo() {
  return <img src="/simbolo.png" alt="" width={40} height={34} />;
}

export function BarraLateral() {
  const { usuario, sair } = useSessao();
  const gestao = usuario?.role === 'admin' || usuario?.role === 'coordenador';
  const itens =
    usuario?.role === 'aluno'
      ? ITENS_DO_ALUNO
      : [...ITENS, ...(gestao ? ITENS_DA_GESTAO : []), ITEM_PERFIL];

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
