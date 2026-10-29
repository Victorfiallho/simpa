import { FileSpreadsheet, FileText, FileType2 } from 'lucide-react';
import { useState } from 'react';

import { baixar } from '../api/cliente';
import type { Painel, Situacao } from '../api/tipos';
import { ORDEM_SITUACAO, ROTULO_SITUACAO } from '../dados/formato';

type Formato = 'csv' | 'xlsx' | 'pdf';

const FORMATOS: { formato: Formato; titulo: string; descricao: string; Icone: typeof FileText }[] = [
  { formato: 'csv', titulo: 'CSV', descricao: 'Abre no Excel e no Google Planilhas', Icone: FileText },
  { formato: 'xlsx', titulo: 'Excel (XLSX)', descricao: 'Planilha formatada, pronta para filtrar', Icone: FileSpreadsheet },
  { formato: 'pdf', titulo: 'PDF', descricao: 'Para imprimir ou anexar', Icone: FileType2 },
];

interface Props {
  painel: Painel;
  turmaId: number | null;
  periodo: string | null;
}

export function Relatorios({ painel, turmaId, periodo }: Props) {
  const [situacao, setSituacao] = useState<Situacao | ''>('');
  const [baixando, setBaixando] = useState<Formato | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const inscricoes = painel.alunos.flatMap((a) => a.inscricoes);
  const quantidade = situacao ? inscricoes.filter((i) => i.situacao === situacao).length : inscricoes.length;

  async function gerar(formato: Formato) {
    const params = new URLSearchParams({ formato });
    if (turmaId) params.set('turma_id', String(turmaId));
    if (periodo) params.set('periodo_letivo', periodo);
    if (situacao) params.set('situacao', situacao);
    setBaixando(formato);
    setErro(null);
    try {
      await baixar(`/analitico/relatorios/inscricoes?${params}`);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setBaixando(null);
    }
  }

  return (
    <div className="coluna relatorios">
      <section className="cartao">
        <div className="cartao-topo">
          <div>
            <h2>Relatório de inscrições</h2>
            <p className="cartao-sub">
              Notas, frequência, situação e justificativa de cada aluno em cada disciplina. Usa a
              turma e o período escolhidos no topo.
            </p>
          </div>
        </div>

        <div className="ferramentas">
          <label className="campo campo-linha">
            Situação
            <select value={situacao} onChange={(e) => setSituacao(e.target.value as Situacao | '')}>
              <option value="">Todas</option>
              {ORDEM_SITUACAO.map((s) => (
                <option key={s} value={s}>
                  {ROTULO_SITUACAO[s]}
                </option>
              ))}
            </select>
          </label>
          <p className="cartao-sub num">{quantidade} inscrições entram no relatório</p>
        </div>

        <div className="formatos">
          {FORMATOS.map(({ formato, titulo, descricao, Icone }) => (
            <button
              key={formato}
              type="button"
              className="formato"
              onClick={() => gerar(formato)}
              disabled={baixando !== null || quantidade === 0}
            >
              <Icone size={22} aria-hidden="true" />
              <span>
                <strong>{baixando === formato ? 'Gerando…' : titulo}</strong>
                <small>{descricao}</small>
              </span>
            </button>
          ))}
        </div>

        {erro && (
          <p className="erro-campo" role="alert">
            {erro}
          </p>
        )}
        <p className="cartao-sub" style={{ marginTop: 16 }}>
          O arquivo traz data, hora e quem gerou. E-mails saem mascarados e o CPF não sai (LGPD).
        </p>
      </section>
    </div>
  );
}
