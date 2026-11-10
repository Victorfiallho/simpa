import { expect, test } from '@playwright/test';

import { criarAluno, criarCenario, criarProfessor, entrarNaApi, iniciarSessao, inscrever, menu, USUARIOS } from './suporte';

// Cenário 3: o professor enxerga só o seu escopo, inclusive nos dados aninhados de um aluno que
// também cursa a disciplina de outro professor (D03).

test('professor só vê a própria disciplina do aluno compartilhado e nenhum aluno alheio', async ({
  page,
  browser,
}) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const ana = await criarProfessor();
  const bruno = await criarProfessor();

  const a = await criarCenario(admin, ana.api.usuarioId);
  const discB = await admin.post('/academico/disciplinas', {
    nome: `Disciplina do Bruno ${a.disciplina.nome.slice(-8)}`,
    carga_horaria: 60,
    periodo_letivo: '2026.2',
    turma_id: a.turma.id,
    professor_id: bruno.api.usuarioId,
  });
  const inscricaoB = await inscrever(admin, a.aluno.id, discB.id);
  const soDoBruno = await criarAluno(admin, a.turma.id);
  await inscrever(admin, soDoBruno.id, discB.id);
  // Notas diferentes em cada disciplina, para os dados aninhados serem distinguíveis.
  for (const [inscricao, nota] of [
    [a.inscricao.id, '7.00'],
    [inscricaoB.id, '3.00'],
  ] as const) {
    await admin.post('/academico/avaliacoes', {
      inscricao_id: inscricao,
      tipo_avaliacao: 'prova',
      periodo_avaliacao: 'N1',
      nota,
      peso: '4',
    });
  }

  // Professor A (sessão própria).
  await iniciarSessao(page, ana.email);
  await menu(page).getByRole('link', { name: 'Alunos' }).click();
  await page.getByPlaceholder('Buscar por nome ou matrícula').fill(a.aluno.nome_completo);
  await page.getByRole('button', { name: new RegExp(a.aluno.nome_completo) }).click();
  const detalhe = page.getByRole('dialog');
  await expect(detalhe.getByRole('heading', { name: a.aluno.nome_completo })).toBeVisible();
  await expect(detalhe.getByRole('cell', { name: a.disciplina.nome })).toBeVisible();
  await expect(detalhe).not.toContainText(discB.nome);
  await detalhe.getByRole('button').first().click();

  await page.getByPlaceholder('Buscar por nome ou matrícula').fill(soDoBruno.nome_completo);
  await expect(page.getByRole('button', { name: new RegExp(soDoBruno.nome_completo) })).toHaveCount(0);

  // Professor B, em outra sessão de navegador: o espelho do que o A viu.
  const contextoBruno = await browser.newContext();
  const paginaBruno = await contextoBruno.newPage();
  await iniciarSessao(paginaBruno, bruno.email);
  await menu(paginaBruno).getByRole('link', { name: 'Alunos' }).click();
  await paginaBruno.getByPlaceholder('Buscar por nome ou matrícula').fill(a.aluno.nome_completo);
  await paginaBruno.getByRole('button', { name: new RegExp(a.aluno.nome_completo) }).click();
  const detalheBruno = paginaBruno.getByRole('dialog');
  await expect(detalheBruno.getByRole('cell', { name: discB.nome })).toBeVisible();
  await expect(detalheBruno).not.toContainText(a.disciplina.nome);
  await contextoBruno.close();
});
