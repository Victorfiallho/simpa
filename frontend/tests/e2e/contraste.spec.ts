import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

import { criarCenario, criarProfessor, criarUsuarioAluno, entrarNaApi, iniciarSessao, menu, USUARIOS } from './suporte';

// RNF12: contraste mínimo da WCAG 2.1 AA (4,5:1 para texto normal, 3:1 para texto grande),
// conferido pelo axe-core nas telas principais de cada perfil, com os dados já carregados.
// O axe não avalia texto dentro de SVG (eixos dos gráficos): o tom deles é o mesmo --texto-3.

async function semFalhasDeContraste(page: Page, tela: string): Promise<void> {
  // Espera o conteúdo sair do estado "carregando" antes de medir.
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
  const resultado = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze();
  const falhas = resultado.violations.flatMap((v) =>
    v.nodes.map((n) => `${n.target.join(' ')}: ${n.any.map((c) => c.message).join('; ')}`),
  );
  expect(falhas, `contraste insuficiente em ${tela}`).toEqual([]);
}

test('a tela de login tem contraste suficiente', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Entrar', exact: true })).toBeVisible();
  await semFalhasDeContraste(page, 'Login');
});

test('as telas da coordenação têm contraste suficiente', async ({ page }) => {
  test.setTimeout(120_000);
  await iniciarSessao(page, USUARIOS.coordenacao);
  await semFalhasDeContraste(page, 'Visão geral');

  for (const tela of ['Alunos', 'Análises', 'Relatórios', 'Pendências', 'Auditoria', 'Meu perfil']) {
    await menu(page).getByRole('link', { name: tela }).click();
    await expect(page.getByRole('banner').getByRole('heading', { name: tela })).toBeVisible();
    await semFalhasDeContraste(page, tela);
  }
});

test('as telas de cadastro e lançamento do admin têm contraste suficiente', async ({ page }) => {
  await iniciarSessao(page, USUARIOS.admin);
  for (const tela of ['Cadastros', 'Lançamentos']) {
    await menu(page).getByRole('link', { name: tela }).click();
    await expect(page.getByRole('banner').getByRole('heading', { name: tela })).toBeVisible();
    await semFalhasDeContraste(page, tela);
  }
});

test('as telas do aluno têm contraste suficiente', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);
  await admin.post('/academico/avaliacoes', {
    inscricao_id: c.inscricao.id,
    tipo_avaliacao: 'prova',
    periodo_avaliacao: 'N1',
    nota: '4.00',
    peso: '4',
  });
  criarUsuarioAluno(c.aluno.id, c.aluno.email);

  await iniciarSessao(page, c.aluno.email);
  await semFalhasDeContraste(page, 'Meu desempenho');
  await menu(page).getByRole('link', { name: 'Pedir apoio' }).click();
  await semFalhasDeContraste(page, 'Pedir apoio');
});
