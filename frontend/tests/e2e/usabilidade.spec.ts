import { expect, test } from '@playwright/test';

import { criarCenario, criarProfessor, entrarNaApi, iniciarSessao, menu, USUARIOS } from './suporte';

// Telas baixas (notebook de 768 px): o menu da gestão tem 11 itens e não cabe na janela. Todos
// precisam continuar alcançáveis, e o perfil (nome e "Sair") continua visível embaixo.

for (const viewport of [
  { width: 1280, height: 720 },
  { width: 1366, height: 768 },
]) {
  test(`o menu da coordenação é alcançável em ${viewport.width}×${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await iniciarSessao(page, USUARIOS.coordenacao);

    for (const [item, titulo] of [
      ['Pendências', 'Pendências'],
      ['Auditoria', 'Auditoria'],
      ['Meu perfil', 'Meu perfil'],
    ]) {
      await menu(page).getByRole('link', { name: item }).click();
      await expect(page.getByRole('banner').getByRole('heading', { name: titulo })).toBeVisible();
    }
    await expect(page.getByRole('button', { name: 'Sair' })).toBeInViewport();
  });
}

test('a situação de risco aparece escrita, e não só pela cor (RNF12)', async ({ page }) => {
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
  await admin.post('/academico/frequencias', {
    inscricao_id: c.inscricao.id,
    periodo_avaliacao: 'N1',
    aulas_previstas: 32,
    faltas: 2,
  });

  await iniciarSessao(page, USUARIOS.coordenacao);
  await menu(page).getByRole('link', { name: 'Alunos' }).click();
  await page.getByPlaceholder('Buscar por nome ou matrícula').fill(c.aluno.nome_completo);

  const linha = page.getByRole('row').filter({ hasText: c.aluno.nome_completo });
  await expect(linha).toContainText('Em risco');
});
