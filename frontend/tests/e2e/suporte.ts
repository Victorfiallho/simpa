// Apoio dos testes de navegador: dados criados pela API real, usuários de teste e controle do Compose.
// Nada aqui usa dados reais nem o ambiente de desenvolvimento: só o projeto `simpa-test`.

import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { expect, type Page } from '@playwright/test';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
export const BASE_URL = process.env.SIMPA_BASE_URL ?? 'http://127.0.0.1:18080';
const ARQUIVO_ENV = path.join(RAIZ, '.env.test');
const COMPOSE = ['compose', '--env-file', ARQUIVO_ENV, '-p', 'simpa-test', '-f', path.join(RAIZ, 'compose.test.yml')];

/** Lê uma variável do .env.test (sintético) ou do ambiente. */
function lerEnv(nome: string): string {
  if (process.env[nome]) return process.env[nome] as string;
  const linha = readFileSync(ARQUIVO_ENV, 'utf-8')
    .split('\n')
    .find((l) => l.startsWith(`${nome}=`));
  if (!linha) throw new Error(`${nome} não encontrada em .env.test`);
  return linha.slice(nome.length + 1).trim();
}

export const SENHA = lerEnv('DEMO_SENHA');

export const USUARIOS = {
  admin: 'admin@simpa.dev',
  coordenacao: 'coordenacao@simpa.dev',
  ana: 'ana.prof@simpa.dev',
  bruno: 'bruno.prof@simpa.dev',
} as const;

export function unico(): string {
  return Math.random().toString(16).slice(2, 10);
}

// ---------- Compose (só o ambiente de teste) ----------

function compose(args: string[], env: Record<string, string> = {}): string {
  return execFileSync('docker', [...COMPOSE, ...args], {
    cwd: RAIZ,
    encoding: 'utf-8',
    env: { ...process.env, ...env },
    timeout: 60_000,
  }).trim();
}

const CRIAR_USUARIO = `
import os
from app.core.database import get_sessionmaker
from app.services.usuarios import criar_usuario
aluno = os.environ.get("ALUNO_ID")
with get_sessionmaker()() as db:
    criar_usuario(db, os.environ["NOME"], os.environ["EMAIL"], os.environ["SENHA"], os.environ["PAPEL"], int(aluno) if aluno else None)
`;

/** Cria um usuário no auth de teste (o auth não tem rota para isso). Só existe neste ambiente. */
function criarUsuario(papel: 'aluno' | 'professor', email: string, alunoId?: number): void {
  const env: Record<string, string> = { NOME: `${papel}.e2e.${unico()}`, EMAIL: email, SENHA, PAPEL: papel };
  const repassadas = ['-e', 'NOME', '-e', 'EMAIL', '-e', 'SENHA', '-e', 'PAPEL'];
  if (alunoId !== undefined) {
    env.ALUNO_ID = String(alunoId);
    repassadas.push('-e', 'ALUNO_ID');
  }
  compose(['exec', '-T', ...repassadas, 'auth', 'python', '-c', CRIAR_USUARIO], env);
}

/** Cria o usuário (perfil aluno) ligado a um aluno do acadêmico. */
export function criarUsuarioAluno(alunoId: number, email: string): void {
  criarUsuario('aluno', email, alunoId);
}

/**
 * Professor novo, só do teste: ele enxerga apenas as disciplinas que o próprio teste criou, sem
 * depender do que os outros testes deixaram no ambiente.
 */
export async function criarProfessor(): Promise<{ email: string; api: Api }> {
  const email = `prof.${unico()}@exemplo.com`;
  criarUsuario('professor', email);
  return { email, api: await entrarNaApi(email) };
}

const TOKEN_EXPIRADO = `
import jwt
from datetime import UTC, datetime, timedelta
from app.core import seguranca as s
agora = datetime.now(UTC)
print(jwt.encode(
    {"sub": "3", "nome": "ana", "role": "professor", "iss": s.EMISSOR,
     "iat": agora - timedelta(hours=2), "exp": agora - timedelta(hours=1)},
    s.chave_privada(), algorithm=s.ALGORITMO, headers={"kid": s.KID},
))
`;

/** JWT assinado de verdade pelo auth, mas já vencido há uma hora: quem recusa é o backend. */
export function tokenExpirado(): string {
  const token = compose(['exec', '-T', 'auth', 'python', '-c', TOKEN_EXPIRADO]);
  if (token.split('.').length !== 3) throw new Error('o auth não devolveu um JWT');
  return token;
}

// ---------- API (dados dos cenários) ----------

/**
 * Cliente de API dos testes. Usa o `fetch` do Node, e não o contexto de API do Playwright, de
 * propósito: o Playwright grava as requisições dele no trace, e o trace levaria a senha do
 * ambiente de teste (do login) e o token de cada chamada de preparação de dados.
 */
export interface Api {
  usuarioId: number;
  post<T = any>(caminho: string, corpo: unknown, esperado?: number): Promise<T>;
  get<T = any>(caminho: string): Promise<T>;
}

async function chamar(token: string, metodo: 'GET' | 'POST', caminho: string, corpo?: unknown): Promise<Response> {
  return fetch(`${BASE_URL}/api${caminho}`, {
    method: metodo,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
}

/** Login pela API (sem aparecer no trace). Devolve a resposta `dados` do auth. */
export async function loginPelaApi(email: string, senha = SENHA): Promise<any> {
  const resposta = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, senha }),
  });
  expect(resposta.status, `login de ${email}`).toBe(200);
  return (await resposta.json()).dados;
}

export async function entrarNaApi(email: string, senha = SENHA): Promise<Api> {
  const dados = await loginPelaApi(email, senha);
  const token: string = dados.access_token;
  return {
    usuarioId: dados.usuario.id,
    async post(caminho, corpo, esperado = 201) {
      const r = await chamar(token, 'POST', caminho, corpo);
      const texto = await r.text();
      expect(r.status, `POST ${caminho}: ${texto}`).toBe(esperado);
      return JSON.parse(texto).dados;
    },
    async get(caminho) {
      const r = await chamar(token, 'GET', caminho);
      const texto = await r.text();
      expect(r.status, `GET ${caminho}: ${texto}`).toBe(200);
      return JSON.parse(texto).dados;
    },
  };
}

export interface Cenario {
  turma: { id: number; nome: string };
  disciplina: { id: number; nome: string };
  aluno: { id: number; matricula: string; nome_completo: string; email: string };
  inscricao: { id: number };
}

/** Turma, disciplina de um professor, aluno e inscrição novos (nomes únicos). */
export async function criarCenario(admin: Api, professorId: number, turma?: Cenario['turma']): Promise<Cenario> {
  const sufixo = unico();
  const turmaCriada =
    turma ??
    (await admin.post('/academico/turmas', {
      nome: `Turma e2e ${sufixo}`,
      curso: 'Inteligência Artificial',
      periodo_letivo: '2026.2',
      turno: 'noturno',
    }));
  const disciplina = await admin.post('/academico/disciplinas', {
    nome: `Disciplina e2e ${sufixo}`,
    carga_horaria: 60,
    periodo_letivo: '2026.2',
    turma_id: turmaCriada.id,
    professor_id: professorId,
  });
  const aluno = await criarAluno(admin, turmaCriada.id);
  const inscricao = await admin.post('/academico/inscricoes', { aluno_id: aluno.id, disciplina_id: disciplina.id });
  return { turma: turmaCriada, disciplina, aluno, inscricao };
}

export async function criarAluno(admin: Api, turmaId: number): Promise<Cenario['aluno']> {
  const sufixo = unico();
  return admin.post('/academico/alunos', {
    matricula: `7${Math.floor(Math.random() * 1e9).toString().padStart(9, '0')}`,
    nome_completo: `Aluno E2E ${sufixo}`,
    email: `aluno.${sufixo}@exemplo.com`,
    curso: 'Inteligência Artificial',
    turma_id: turmaId,
  });
}

export async function inscrever(admin: Api, alunoId: number, disciplinaId: number): Promise<{ id: number }> {
  return admin.post('/academico/inscricoes', { aluno_id: alunoId, disciplina_id: disciplinaId });
}

// ---------- Interface ----------

/** Entra pela tela de login, como uma pessoa. Devolve quando o menu principal aparece. */
export async function entrarNaTela(page: Page, email: string, senha = SENHA): Promise<void> {
  await page.goto('/');
  await page.getByLabel('E-mail institucional').fill(email);
  await page.getByPlaceholder('Digite sua senha').fill(senha);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page.getByRole('navigation', { name: 'Menu principal' })).toBeVisible();
}

/**
 * Inicia a sessão sem digitar a senha na tela: faz o login pela API e entrega a sessão ao navegador,
 * como a própria tela faria. Só `login.spec.ts` usa a tela de login. Assim a senha do ambiente de
 * teste não aparece nos traces dos demais testes (o token, de curta duração, ainda aparece).
 */
export async function iniciarSessao(page: Page, email: string): Promise<void> {
  const dados = await loginPelaApi(email);
  await page.addInitScript(
    ([token, usuario, minutos]) => {
      sessionStorage.setItem(
        'simpa.sessao',
        JSON.stringify({ token, usuario, expiraEm: Date.now() + Number(minutos) * 60_000 }),
      );
    },
    [dados.access_token, dados.usuario, dados.expira_em_minutos],
  );
  await page.goto('/');
  await expect(menu(page)).toBeVisible();
}

export function menu(page: Page) {
  return page.getByRole('navigation', { name: 'Menu principal' });
}
