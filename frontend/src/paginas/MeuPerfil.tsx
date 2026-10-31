import { type FormEvent, useEffect, useState } from 'react';

import { api } from '../api/cliente';
import type { Perfil, Resposta } from '../api/tipos';
import { useDados } from '../api/useDados';
import { Conteudo } from '../componentes/Conteudo';

const CAMPOS = [
  ['nome_completo', 'Nome completo'],
  ['telefone', 'Telefone (com DDD)'],
  ['email_contato', 'E-mail de contato'],
  ['cidade', 'Cidade'],
  ['uf', 'UF'],
] as const;
type Campo = (typeof CAMPOS)[number][0];

/** Dados pessoais do próprio usuário, de qualquer perfil. O CPF nunca aparece aqui (RNF04). */
export function MeuPerfil() {
  const perfil = useDados(() => api<Resposta<Perfil>>('/auth/me').then((r) => r.dados), []);
  return <Conteudo estado={perfil}>{(p) => <Formulario perfil={p} aoSalvar={perfil.recarregar} />}</Conteudo>;
}

function inicial(perfil: Perfil): Record<Campo, string> {
  return Object.fromEntries(CAMPOS.map(([c]) => [c, perfil[c] ?? ''])) as Record<Campo, string>;
}

function Formulario({ perfil, aoSalvar }: { perfil: Perfil; aoSalvar: () => void }) {
  const [valores, setValores] = useState<Record<Campo, string>>(() => inicial(perfil));
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => setValores(inicial(perfil)), [perfil]);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setSalvando(true);
    setErro(null);
    setMensagem(null);
    // Campo vazio vira null, que limpa o dado no servidor.
    const corpo = Object.fromEntries(CAMPOS.map(([c]) => [c, valores[c].trim() || null]));
    try {
      await api('/auth/me', { method: 'PATCH', body: JSON.stringify(corpo) });
      setMensagem('Perfil atualizado.');
      aoSalvar();
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section className="cartao">
      <div className="cartao-topo">
        <div>
          <h2>Meu perfil</h2>
          <p className="cartao-sub">
            Usuário {perfil.nome_usuario} · {perfil.preenchimento_percentual}% preenchido
          </p>
        </div>
      </div>
      <form className="coluna" onSubmit={salvar}>
        {CAMPOS.map(([campo, rotulo]) => (
          <label key={campo} className="campo">
            {rotulo}
            <input
              value={valores[campo]}
              maxLength={campo === 'uf' ? 2 : 80}
              onChange={(e) => setValores({ ...valores, [campo]: e.target.value })}
            />
          </label>
        ))}
        {erro && (
          <p className="erro-campo" role="alert">
            {erro}
          </p>
        )}
        {mensagem && <p role="status">{mensagem}</p>}
        <button type="submit" className="botao-primario" disabled={salvando}>
          {salvando ? 'Salvando…' : 'Salvar'}
        </button>
      </form>
    </section>
  );
}
