import { Eye, EyeOff } from 'lucide-react';
import { type FormEvent, useState } from 'react';

import { useSessao } from '../sessao';

/** Linhas decorativas do painel escuro: uma trajetória com pontos e duas de referência. */
function Trajetoria() {
  return (
    <svg className="login-grafico" viewBox="0 0 660 240" preserveAspectRatio="xMinYMax slice" aria-hidden="true">
      <path d="M0 210 C 120 170, 200 160, 330 175 S 520 120, 660 110" fill="none" stroke="#5c5a54" strokeWidth="1.5" />
      <path d="M350 205 C 450 195, 560 140, 660 145" fill="none" stroke="#5c5a54" strokeWidth="1.5" strokeDasharray="5 6" />
      <path
        d="M0 185 C 40 175, 70 165, 110 150 S 200 110, 250 108 S 310 130, 345 128 S 420 85, 467 70"
        fill="none"
        stroke="#8ca573"
        strokeWidth="2"
      />
      <path d="M467 70 L 660 0" fill="none" stroke="#8ca573" strokeWidth="2" strokeDasharray="6 7" />
      {[
        [110, 150],
        [250, 108],
        [345, 128],
        [467, 70],
      ].map(([x, y]) => (
        <circle key={x} cx={x} cy={y} r="6" fill="#8ca573" />
      ))}
    </svg>
  );
}

export function Login() {
  const { entrar, expirou } = useSessao();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [verSenha, setVerSenha] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
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

  const limparMensagens = () => {
    setErro(null);
    setAviso(null);
  };

  return (
    <div className="login">
      <section className="login-apresentacao">
        <img src="/logo-claro.png" alt="SIMPA" width={210} height={45} />
        <div className="login-chamada">
          <h1>Cada trajetória acadêmica merece atenção.</h1>
          <p>Dados que ajudam a identificar riscos e orientar o acompanhamento dos alunos.</p>
        </div>
        <Trajetoria />
      </section>

      <main className="login-lado">
        <form className="login-form" onSubmit={enviar} noValidate>
          <p className="sobretitulo">Acesso ao sistema</p>
          <h2>Entre no SIMPA</h2>
          <p className="subtitulo">Acesse sua conta para acompanhar os alunos.</p>

          {expirou && !erro && <p className="aviso">Sua sessão expirou. Entre de novo.</p>}

          <label className="campo">
            E-mail institucional
            <input
              type="email"
              autoComplete="username"
              placeholder="voce@instituicao.edu.br"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                limparMensagens();
              }}
              autoFocus
            />
          </label>

          <label className="campo">
            Senha
            <span className="senha">
              <input
                type={verSenha ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Digite sua senha"
                value={senha}
                onChange={(e) => {
                  setSenha(e.target.value);
                  limparMensagens();
                }}
              />
              <button
                type="button"
                onClick={() => setVerSenha((v) => !v)}
                aria-label={verSenha ? 'Esconder a senha' : 'Mostrar a senha'}
                aria-pressed={verSenha}
              >
                {verSenha ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </span>
          </label>

          <button
            type="button"
            className="esqueci"
            onClick={() => setAviso('Para redefinir a senha, fale com a coordenação do curso.')}
          >
            Esqueci minha senha
          </button>

          {erro && (
            <p className="erro-campo" role="alert">
              {erro}
            </p>
          )}
          {aviso && (
            <p className="aviso" role="status">
              {aviso}
            </p>
          )}

          <button type="submit" className="botao-primario" disabled={enviando}>
            {enviando ? 'Entrando…' : 'Entrar'}
          </button>

          <p className="login-ajuda">Precisa de acesso? Fale com a coordenação.</p>
        </form>

        <p className="login-rodape">SIMPA · Monitoramento e predição acadêmica</p>
      </main>
    </div>
  );
}
