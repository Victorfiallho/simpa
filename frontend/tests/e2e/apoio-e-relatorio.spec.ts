import { expect, test } from '@playwright/test';

import {
  criarAluno,
  criarCenario,
  criarProfessor,
  criarUsuarioAluno,
  entrarNaApi,
  entrarNaTela,
  menu,
  USUARIOS,
} from './suporte';

// Cenário 7: pedido de apoio do aluno aparece para a coordenação.
// Cenário 8: o relatório é baixado e traz os registros esperados.

test('pedido de apoio criado pelo aluno aparece para a coordenação', async ({ page, browser }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);
  criarUsuarioAluno(c.aluno.id, c.aluno.email);
  const texto = `Preciso de ajuda com a lista de exercícios ${c.aluno.matricula}`;

  await entrarNaTela(page, c.aluno.email);
  await menu(page).getByRole('link', { name: 'Pedir apoio' }).click();
  await page.getByLabel('Motivo').selectOption('Dificuldade com o conteúdo');
  await page.getByLabel('Conte o que está acontecendo').fill(texto);
  await page.getByRole('button', { name: 'Enviar pedido' }).click();
  await expect(page.getByText(texto)).toBeVisible(); // aparece em "Meus pedidos"

  const contextoCoordenacao = await browser.newContext();
  const coordenacao = await contextoCoordenacao.newPage();
  await entrarNaTela(coordenacao, USUARIOS.coordenacao);
  await menu(coordenacao).getByRole('link', { name: 'Pendências' }).click();
  const linha = coordenacao.getByRole('row').filter({ hasText: texto });
  await expect(linha).toBeVisible();
  await expect(linha).toContainText(c.aluno.nome_completo);
  await expect(linha).toContainText('Dificuldade com o conteúdo');
  await expect(linha.getByRole('combobox')).toHaveValue('recebida');
  await contextoCoordenacao.close();
});

test('o relatório CSV é baixado com os registros esperados e o e-mail mascarado', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);
  const outro = await criarAluno(admin, c.turma.id);
  await admin.post('/academico/avaliacoes', {
    inscricao_id: c.inscricao.id,
    tipo_avaliacao: 'prova',
    periodo_avaliacao: 'N1',
    nota: '4.00',
    peso: '4',
  });
  // Sem frequência lançada o sistema ainda não classifica (D09): a situação só sai com os dois dados.
  await admin.post('/academico/frequencias', {
    inscricao_id: c.inscricao.id,
    periodo_avaliacao: 'N1',
    aulas_previstas: 32,
    faltas: 2,
  });

  await entrarNaTela(page, USUARIOS.coordenacao);
  await menu(page).getByRole('link', { name: 'Relatórios' }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: /^CSV/ }).click();
  const arquivo = await download;

  expect(arquivo.suggestedFilename()).toMatch(/^simpa-relatorio-\d{4}-\d{2}-\d{2}\.csv$/);
  const { readFile } = await import('node:fs/promises');
  const conteudo = (await readFile((await arquivo.path()) as string, 'utf-8')).replace(/^﻿/, '');
  const linhas = conteudo.split('\n').map((l) => l.split(';'));
  const cabecalho = linhas.findIndex((l) => l[0] === 'Matrícula');
  expect(cabecalho).toBeGreaterThan(-1);
  const colunas = linhas[cabecalho];
  const registro = linhas.find((l) => l[0] === c.aluno.matricula);
  expect(registro, 'a linha do aluno do cenário está no relatório').toBeTruthy();
  const campo = (nome: string) => (registro as string[])[colunas.indexOf(nome)];

  expect(campo('Aluno')).toBe(c.aluno.nome_completo);
  expect(campo('Disciplina')).toBe(c.disciplina.nome);
  expect(campo('N1')).toBe('4,00');
  expect(campo('Situação')).toBe('Em risco');
  expect(campo('E-mail')).toMatch(/\*\*\*@/);
  expect(conteudo).not.toContain(c.aluno.email);
  expect(conteudo).not.toContain(outro.email);
});
