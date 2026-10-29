import { type FormEvent, useState } from 'react';

import { useSessao } from '../sessao';

export function Login() {
  const { entrar, expirou } = useSessao();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!email.trim() || !senha) {
      setErro('Informe o e-mail e a senha.');
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await entrar(email.trim(), senha);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="login">
      <form className="login-cartao" onSubmit={enviar} noValidate>
        <div className="login-marca">
          <h1>
            <img src="/logo.png" alt="SIMPA" width={220} height={47} />
          </h1>
          <p>Sistema Inteligente de Monitoramento e Predição Acadêmica</p>
        </div>

        {expirou && !erro && <p className="aviso">Sua sessão expirou. Entre de novo.</p>}

        <label className="campo">
          E-mail
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setErro(null);
            }}
            autoFocus
          />
        </label>
        <label className="campo">
          Senha
          <input
            type="password"
            autoComplete="current-password"
            value={senha}
            onChange={(e) => {
              setSenha(e.target.value);
              setErro(null);
            }}
          />
        </label>

        {erro && (
          <p className="erro-campo" role="alert">
            {erro}
          </p>
        )}

        <button type="submit" className="botao-primario" disabled={enviando}>
          {enviando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </main>
  );
}
