import { X } from 'lucide-react';
import { useEffect, useRef } from 'react';

import type { AlunoConsolidado, ResumoInscricao } from '../dados/calculos';
import {
  COR_STATUS,
  descreverCriterio,
  formatarNota,
  formatarPercentual,
} from '../dados/formato';
import { Selo } from './Selo';

/** Justificativa legível do status da inscrição (RF07, RNF09). */
function justificar(r: ResumoInscricao): string {
  switch (r.status) {
    case 'indeterminado':
      return 'Sem notas ou sem frequência lançadas. A inscrição fica fora das estatísticas (D09).';
    case 'em_risco': {
      const texto = r.criterios.map((c) => descreverCriterio(c, r.media, r.frequencia)).join(' e ');
      return `${texto[0].toUpperCase()}${texto.slice(1)}.`;
    }
    case 'atencao':
      return 'Acima dos mínimos, mas com média abaixo de 7,00 ou frequência abaixo de 80% (D08).';
    case 'sem_risco':
      return 'Média e frequência acima dos mínimos.';
  }
}

interface Props {
  aluno: AlunoConsolidado;
  periodo: string;
  aoFechar: () => void;
}

export function DetalheAluno({ aluno, periodo, aoFechar }: Props) {
  const fechar = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    fechar.current?.focus();
    const aoTeclar = (e: KeyboardEvent) => e.key === 'Escape' && aoFechar();
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [aoFechar]);

  return (
    <div className="gaveta-fundo" onClick={aoFechar}>
      <aside
        className="gaveta"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-aluno"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="gaveta-topo">
          <div>
            <p className="cartao-sub num">
              Matrícula {aluno.matricula} · Turma {aluno.turma} · {periodo}
            </p>
            <h2 id="titulo-aluno">{aluno.nome}</h2>
          </div>
          <button ref={fechar} type="button" className="botao-icone" onClick={aoFechar}>
            <X size={16} />
            <span className="sr-only">Fechar</span>
          </button>
        </div>

        <div className="resumo-aluno">
          <div className="cartao">
            <span>Média</span>
            <strong className="num">{formatarNota(aluno.media)}</strong>
          </div>
          <div className="cartao">
            <span>Frequência</span>
            <strong className="num">{formatarPercentual(aluno.frequencia)}</strong>
          </div>
          <div className="cartao">
            <span>Situação</span>
            <strong>
              <Selo status={aluno.status} />
            </strong>
          </div>
        </div>

        <section className="cartao">
          <h2>Disciplinas</h2>
          <div className="tabela-rolagem">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Disciplina</th>
                  <th className="direita">N1</th>
                  <th className="direita">N2</th>
                  <th className="direita">Média</th>
                  <th className="direita">Frequência</th>
                  <th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {aluno.resumos.map((r) => (
                  <tr key={r.inscricao.id}>
                    <td>{r.disciplina.nome}</td>
                    <td className="direita num">{formatarNota(r.notaN1)}</td>
                    <td className="direita num">{formatarNota(r.notaN2)}</td>
                    <td className="direita num">{formatarNota(r.media)}</td>
                    <td className="direita num">
                      {formatarPercentual(r.frequencia)}
                      {r.aulas > 0 && (
                        <small style={{ display: 'block', color: 'var(--texto-3)' }}>
                          {r.faltas} faltas em {r.aulas} aulas
                        </small>
                      )}
                    </td>
                    <td>
                      <Selo status={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="cartao-sub" style={{ marginTop: 10 }}>
            Média ponderada: N1 com peso 4 e N2 com peso 6. Arredondamento para 2 casas antes de
            classificar (D06).
          </p>
        </section>

        <div className="motivos">
          {aluno.resumos.map((r) => (
            <div className="motivo" key={r.inscricao.id}>
              <span className="ponto" style={{ color: COR_STATUS[r.status] }} />
              <span>
                <strong>{r.disciplina.nome}:</strong> {justificar(r)}
              </span>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
