import { api } from '../api/cliente';
import type { Painel, Resposta } from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';
import { Selo } from '../componentes/Selo';
import { formatarNota, formatarPercentual } from '../dados/formato';

/** O aluno vê só as próprias notas e faltas: o servidor filtra pelo token. */
export function MeuDesempenho() {
  const painel = useDados(() => api<Resposta<Painel>>('/analitico/meu/painel').then((r) => r.dados), []);
  return (
    <Conteudo estado={painel}>
      {(p) => (
        <div className="coluna">
          <section className="cartao">
            <div className="kpis">
              <div className="kpi">
                <span className="kpi-rotulo">Média geral</span>
                <div className="kpi-valor num">{formatarNota(p.media_geral)}</div>
              </div>
              <div className="kpi">
                <span className="kpi-rotulo">Frequência</span>
                <div className="kpi-valor num">{formatarPercentual(p.frequencia_geral)}</div>
              </div>
              <div className="kpi">
                <span className="kpi-rotulo">Disciplinas</span>
                <div className="kpi-valor num">{p.total_inscricoes}</div>
              </div>
            </div>
          </section>
          <section className="cartao">
            <div className="cartao-topo">
              <h2>Por disciplina</h2>
            </div>
            <div className="tabela-rolagem">
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Disciplina</th>
                    <th>Média</th>
                    <th>Frequência</th>
                    <th>Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {p.dispersao.map((d) => (
                    <tr key={d.disciplina}>
                      <td>{d.disciplina}</td>
                      <td className="num">{formatarNota(d.media)}</td>
                      <td className="num">{formatarPercentual(d.frequencia)}</td>
                      <td>
                        <Selo situacao={d.situacao} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </Conteudo>
  );
}
