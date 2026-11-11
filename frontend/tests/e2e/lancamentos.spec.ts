import { expect, test } from '@playwright/test';

import { criarCenario, criarProfessor, entrarNaApi, iniciarSessao, menu, USUARIOS } from './suporte';

// Cenários 4 e 5: a nota salva permanece depois de recarregar; entrada inválida mostra o erro e
// não altera o que já está gravado.

async function abrirLancamentos(page: import('@playwright/test').Page, disciplina: string, turma: string) {
  await menu(page).getByRole('link', { name: 'Lançamentos' }).click();
  await page.getByRole('combobox', { name: 'Disciplina' }).selectOption({ label: `${disciplina} · ${turma}` });
}

test('nota e faltas salvas permanecem depois de recarregar a página', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);

  await iniciarSessao(page, professor.email);
  await abrirLancamentos(page, c.disciplina.nome, c.turma.nome);
  await page.getByLabel(`Nota N1 de ${c.aluno.nome_completo}`).fill('7,5');
  await page.getByLabel(`Faltas N1 de ${c.aluno.nome_completo}`).fill('2');
  await page.getByRole('button', { name: 'Salvar', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: '2 lançamento(s) salvo(s)' })).toBeVisible();

  await page.reload();
  await abrirLancamentos(page, c.disciplina.nome, c.turma.nome);

  await expect(page.getByLabel(`Nota N1 de ${c.aluno.nome_completo}`)).toHaveValue('7,5');
  await expect(page.getByLabel(`Faltas N1 de ${c.aluno.nome_completo}`)).toHaveValue('2');
  const gravada = await admin.get(`/academico/avaliacoes?inscricao_id=${c.inscricao.id}`);
  expect(gravada.map((n: { nota: string }) => n.nota)).toEqual(['7.50']);
});

test('nota inválida mostra o erro e não altera o que já estava gravado', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);
  await admin.post('/academico/avaliacoes', {
    inscricao_id: c.inscricao.id,
    tipo_avaliacao: 'prova',
    periodo_avaliacao: 'N1',
    nota: '7.50',
    peso: '4',
  });

  await iniciarSessao(page, professor.email);
  await abrirLancamentos(page, c.disciplina.nome, c.turma.nome);
  const campo = page.getByLabel(`Nota N1 de ${c.aluno.nome_completo}`);
  await expect(campo).toHaveValue('7,5');
  await campo.fill('11');
  await page.getByRole('button', { name: 'Salvar', exact: true }).click();

  await expect(page.getByRole('alert').filter({ hasText: 'Nota N1: use um valor de 0 a 10.' })).toBeVisible();
  await page.reload();
  await abrirLancamentos(page, c.disciplina.nome, c.turma.nome);
  await expect(page.getByLabel(`Nota N1 de ${c.aluno.nome_completo}`)).toHaveValue('7,5');
  const gravada = await admin.get(`/academico/avaliacoes?inscricao_id=${c.inscricao.id}`);
  expect(gravada.map((n: { nota: string }) => n.nota)).toEqual(['7.50']);
});
