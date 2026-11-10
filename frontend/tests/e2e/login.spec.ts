import { expect, test } from '@playwright/test';

import {
  criarAluno,
  criarUsuarioAluno,
  entrarNaApi,
  entrarNaTela,
  menu,
  tokenExpirado,
  unico,
  USUARIOS,
} from './suporte';

// Cenários 1, 2 e 6: login válido por perfil, login inválido e sessão expirada.

const PERFIS = [
  {
    nome: 'administração',
    email: USUARIOS.admin,
    com: ['Cadastros', 'Lançamentos', 'Alertas', 'Auditoria'],
    sem: [],
  },
  {
    nome: 'coordenação',
    email: USUARIOS.coordenacao,
    com: ['Cadastros', 'Alertas', 'Auditoria'],
    sem: ['Lançamentos'],
  },
  {
    nome: 'professor',
    email: USUARIOS.ana,
    com: ['Alunos', 'Lançamentos'],
    sem: ['Cadastros', 'Alertas', 'Auditoria'],
  },
];

for (const perfil of PERFIS) {
  test(`login válido: ${perfil.nome} vê só o menu do seu perfil`, async ({ page }) => {
    await entrarNaTela(page, perfil.email);

    for (const item of perfil.com) await expect(menu(page).getByRole('link', { name: item })).toBeVisible();
    for (const item of perfil.sem) await expect(menu(page).getByRole('link', { name: item })).toHaveCount(0);
  });
}

test('login válido: o aluno vê só as telas dele', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const turma = await admin.post('/academico/turmas', {
    nome: `Turma e2e ${unico()}`,
    curso: 'Inteligência Artificial',
    periodo_letivo: '2026.2',
    turno: 'noturno',
  });
  const aluno = await criarAluno(admin, turma.id);
  criarUsuarioAluno(aluno.id, aluno.email);

  await entrarNaTela(page, aluno.email);

  await expect(menu(page).getByRole('link', { name: 'Meu desempenho' })).toBeVisible();
  await expect(menu(page).getByRole('link', { name: 'Pedir apoio' })).toBeVisible();
  for (const item of ['Alunos', 'Cadastros', 'Lançamentos', 'Auditoria']) {
    await expect(menu(page).getByRole('link', { name: item })).toHaveCount(0);
  }
});

test('login inválido: mensagem genérica, sem revelar se foi o e-mail ou a senha', async ({ page }) => {
  await page.goto('/');
  // E-mail que não existe: não gasta tentativas de nenhum usuário real (há bloqueio por e-mail).
  await page.getByLabel('E-mail institucional').fill(`ninguem.${unico()}@exemplo.com`);
  await page.getByPlaceholder('Digite sua senha').fill('senhaQueNaoExiste123');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();

  await expect(page.getByRole('alert')).toHaveText('E-mail ou senha inválidos.');
  await expect(menu(page)).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Entre no SIMPA' })).toBeVisible();
});

test('sessão expirada: o servidor recusa o token e a pessoa volta ao login', async ({ page }) => {
  // JWT assinado de verdade pelo auth, mas vencido. O `expiraEm` da sessão do navegador fica no
  // futuro de propósito: se a tela confiasse só no relógio, entraria; quem recusa é o backend.
  const token = tokenExpirado();
  await page.addInitScript((t) => {
    sessionStorage.setItem(
      'simpa.sessao',
      JSON.stringify({
        token: t,
        usuario: { id: 3, nome_usuario: 'ana', role: 'professor' },
        expiraEm: Date.now() + 60 * 60 * 1000,
      }),
    );
  }, token);

  const recusa = page.waitForResponse((r) => r.url().includes('/api/') && r.status() === 401);
  await page.goto('/');
  const resposta = await recusa;

  expect(resposta.request().headers()['authorization']).toBe(`Bearer ${token}`);
  await expect(page.getByRole('heading', { name: 'Entre no SIMPA' })).toBeVisible();
  await expect(page.getByText('Sua sessão expirou. Entre de novo.')).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('simpa.sessao'))).toBeNull();
});
