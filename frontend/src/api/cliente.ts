// Cliente HTTP do frontend. Fala só com o gateway (/api/...) e envia o token em toda chamada.

import type { Resposta, Token, Usuario } from './tipos';

const CHAVE_SESSAO = 'simpa.sessao';

export interface Sessao {
  token: string;
  usuario: Usuario;
  expiraEm: number;
}

/** A sessão fica no sessionStorage: some ao fechar a aba. */
export function lerSessao(): Sessao | null {
  try {
    const sessao = JSON.parse(sessionStorage.getItem(CHAVE_SESSAO) ?? 'null') as Sessao | null;
    return sessao && sessao.expiraEm > Date.now() ? sessao : null;
  } catch {
    return null;
  }
}

function gravarSessao(sessao: Sessao | null) {
  try {
    if (sessao) sessionStorage.setItem(CHAVE_SESSAO, JSON.stringify(sessao));
    else sessionStorage.removeItem(CHAVE_SESSAO);
  } catch {
    // Sem armazenamento (aba privada restrita): a sessão vale só até recarregar a página.
  }
}

let aoExpirar: (() => void) | null = null;

/** Avisa o app quando o token expira ou é recusado, para voltar à tela de login. */
export function quandoExpirar(callback: () => void) {
  aoExpirar = callback;
}

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    readonly codigo: string,
    mensagem: string,
  ) {
    super(mensagem);
  }
}

async function requisitar(caminho: string, opcoes: RequestInit = {}): Promise<Response> {
  const sessao = lerSessao();
  const cabecalhos = new Headers(opcoes.headers);
  if (sessao) cabecalhos.set('Authorization', `Bearer ${sessao.token}`);
  if (opcoes.body) cabecalhos.set('Content-Type', 'application/json');

  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, { ...opcoes, headers: cabecalhos });
  } catch {
    throw new ErroApi(0, 'SEM_CONEXAO', 'Não foi possível falar com o servidor.');
  }

  if (resposta.status === 401 && sessao) {
    gravarSessao(null);
    aoExpirar?.();
  }
  if (!resposta.ok) {
    const corpo = (await resposta.json().catch(() => null)) as Resposta<unknown> | null;
    throw new ErroApi(
      resposta.status,
      corpo?.erro?.codigo ?? 'ERRO',
      corpo?.mensagem ?? 'Não foi possível completar a operação.',
    );
  }
  return resposta;
}

export async function api<T>(caminho: string, opcoes?: RequestInit): Promise<T> {
  return (await requisitar(caminho, opcoes)).json() as Promise<T>;
}

export async function entrar(email: string, senha: string): Promise<Sessao> {
  const resposta = await api<Resposta<Token>>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, senha }),
  });
  const sessao: Sessao = {
    token: resposta.dados.access_token,
    usuario: resposta.dados.usuario,
    expiraEm: Date.now() + resposta.dados.expira_em_minutos * 60_000,
  };
  gravarSessao(sessao);
  return sessao;
}

export function sair() {
  gravarSessao(null);
}

/** Baixa um arquivo autenticado (relatórios) e entrega ao navegador. */
export async function baixar(caminho: string): Promise<void> {
  const resposta = await requisitar(caminho);
  const nome =
    /filename="([^"]+)"/.exec(resposta.headers.get('Content-Disposition') ?? '')?.[1] ??
    'simpa-relatorio';
  const url = URL.createObjectURL(await resposta.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = nome;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
