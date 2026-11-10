import { expect, type Page, test } from '@playwright/test';

import { criarCenario, criarProfessor, entrarNaApi, iniciarSessao, menu, unico, USUARIOS } from './suporte';

// Telas de Cadastros (RF01, RF02): admin e coordenação cadastram turmas, disciplinas, alunos e
// inscrições. O professor não vê esta tela (D03).

async function abrirCadastros(page: Page, aba: 'Turmas' | 'Disciplinas' | 'Alunos' | 'Inscrições') {
  await menu(page).getByRole('link', { name: 'Cadastros' }).click();
  await page.getByRole('group', { name: 'Tipo de cadastro' }).getByRole('button', { name: aba }).click();
}

test('a coordenação cadastra turma, disciplina, aluno e inscreve pela matrícula', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const sufixo = unico();
  const turma = `Turma cadastro ${sufixo}`;
  const disciplina = `Disciplina cadastro ${sufixo}`;
  const aluno = `Aluno cadastro ${sufixo}`;
  const matricula = `6${Math.floor(Math.random() * 1e9).toString().padStart(9, '0')}`;

  await iniciarSessao(page, USUARIOS.coordenacao);

  // Turma
  await abrirCadastros(page, 'Turmas');
  await page.getByRole('button', { name: 'Nova turma' }).click();
  const formTurma = page.getByRole('dialog', { name: 'Nova turma' });
  await formTurma.getByRole('textbox', { name: 'Nome da turma' }).fill(turma);
  await formTurma.getByRole('textbox', { name: 'Curso' }).fill('Inteligência Artificial');
  await formTurma.getByRole('textbox', { name: 'Período letivo' }).fill('2026.2');
  await formTurma.getByRole('combobox', { name: 'Turno' }).selectOption('noturno');
  await formTurma.getByRole('button', { name: 'Cadastrar' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Turma cadastrada.' })).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: turma })).toBeVisible();

  // Disciplina, com o professor da demonstração
  await abrirCadastros(page, 'Disciplinas');
  await page.getByRole('button', { name: 'Nova disciplina' }).click();
  const formDisciplina = page.getByRole('dialog', { name: 'Nova disciplina' });
  await formDisciplina.getByRole('textbox', { name: 'Nome da disciplina' }).fill(disciplina);
  await formDisciplina.getByRole('combobox', { name: 'Turma' }).selectOption({ label: `${turma} · 2026.2` });
  await formDisciplina.getByRole('textbox', { name: 'Período letivo' }).fill('2026.2');
  await formDisciplina.getByRole('spinbutton', { name: 'Carga horária' }).fill('60');
  await formDisciplina.getByRole('spinbutton', { name: 'Professor responsável' }).fill(String(professor.api.usuarioId));
  await formDisciplina.getByRole('button', { name: 'Cadastrar' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Disciplina cadastrada.' })).toBeVisible();

  // Aluno
  await abrirCadastros(page, 'Alunos');
  await page.getByRole('button', { name: 'Novo aluno' }).click();
  const formAluno = page.getByRole('dialog', { name: 'Novo aluno' });
  await formAluno.getByRole('textbox', { name: 'Matrícula' }).fill(matricula);
  await formAluno.getByRole('textbox', { name: 'Nome completo' }).fill(aluno);
  await formAluno.getByRole('textbox', { name: 'E-mail' }).fill(`aluno.${sufixo}@exemplo.com`);
  await formAluno.getByRole('textbox', { name: 'Curso' }).fill('Inteligência Artificial');
  await formAluno.getByRole('combobox', { name: 'Turma' }).selectOption({ label: `${turma} · 2026.2` });
  await formAluno.getByRole('button', { name: 'Cadastrar' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Aluno cadastrado.' })).toBeVisible();
  await page.getByPlaceholder('Buscar por nome ou matrícula').fill(aluno);
  await expect(page.getByRole('row').filter({ hasText: matricula })).toBeVisible();

  // Inscrição, pela matrícula
  await abrirCadastros(page, 'Inscrições');
  await page.getByRole('combobox', { name: 'Disciplina' }).selectOption({ label: `${disciplina} · ${turma}` });
  await page.getByRole('textbox', { name: 'Matrícula do aluno' }).fill(matricula);
  await page.getByRole('button', { name: 'Inscrever' }).click();
  await expect(page.getByRole('status').filter({ hasText: `${aluno} inscrito(a) em ${disciplina}` })).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: aluno })).toContainText('Ativa');

  // O que a tela mostra está mesmo gravado.
  const gravada = await admin.get(`/academico/alunos/matricula/${matricula}`);
  expect(gravada.nome_completo).toBe(aluno);
  expect(gravada.inscricoes.map((i: { disciplina: { nome: string } }) => i.disciplina.nome)).toEqual([disciplina]);
});

test('dados inválidos mostram qual campo falhou e nada é criado', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const existente = await criarCenario(admin, professor.api.usuarioId);
  const nomeTurma = `Turma invalida ${unico()}`;

  await iniciarSessao(page, USUARIOS.coordenacao);

  await abrirCadastros(page, 'Turmas');
  await page.getByRole('button', { name: 'Nova turma' }).click();
  const formTurma = page.getByRole('dialog', { name: 'Nova turma' });
  await formTurma.getByRole('textbox', { name: 'Nome da turma' }).fill(nomeTurma);
  await formTurma.getByRole('textbox', { name: 'Curso' }).fill('IA');
  await formTurma.getByRole('textbox', { name: 'Período letivo' }).fill('abc');
  await formTurma.getByRole('combobox', { name: 'Turno' }).selectOption('noturno');
  await formTurma.getByRole('button', { name: 'Cadastrar' }).click();
  await expect(formTurma.getByRole('alert')).toContainText('periodo_letivo');
  await formTurma.getByRole('button', { name: 'Fechar' }).click();
  const turmas = await admin.get(`/academico/turmas?limite=100&ordenar_por=id&ordem=desc`);
  expect(turmas.map((t: { nome: string }) => t.nome)).not.toContain(nomeTurma);

  // Matrícula repetida: o servidor recusa e a mensagem aparece no formulário.
  await abrirCadastros(page, 'Alunos');
  await page.getByRole('button', { name: 'Novo aluno' }).click();
  const formAluno = page.getByRole('dialog', { name: 'Novo aluno' });
  await formAluno.getByRole('textbox', { name: 'Matrícula' }).fill(existente.aluno.matricula);
  await formAluno.getByRole('textbox', { name: 'Nome completo' }).fill('Duplicado');
  await formAluno.getByRole('textbox', { name: 'E-mail' }).fill(`dup.${unico()}@exemplo.com`);
  await formAluno.getByRole('textbox', { name: 'Curso' }).fill('Inteligência Artificial');
  await formAluno.getByRole('combobox', { name: 'Turma' }).selectOption({ label: `${existente.turma.nome} · 2026.2` });
  await formAluno.getByRole('button', { name: 'Cadastrar' }).click();
  await expect(formAluno.getByRole('alert')).toContainText(`A matrícula ${existente.aluno.matricula} já está cadastrada`);
});

test('editar um aluno não mostra o CPF e inativar mantém o histórico', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);
  const novoNome = `Aluno renomeado ${unico()}`;

  await iniciarSessao(page, USUARIOS.coordenacao);
  await abrirCadastros(page, 'Alunos');
  await page.getByPlaceholder('Buscar por nome ou matrícula').fill(c.aluno.nome_completo);

  await page.getByRole('button', { name: `Editar ${c.aluno.nome_completo}` }).click();
  const form = page.getByRole('dialog', { name: 'Editar aluno' });
  await expect(form.getByRole('textbox', { name: 'CPF' })).toHaveValue(''); // privacidade: nunca volta do servidor
  await form.getByRole('textbox', { name: 'Nome completo' }).fill(novoNome);
  await form.getByRole('button', { name: 'Salvar alterações' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Alterações salvas.' })).toBeVisible();
  await page.getByPlaceholder('Buscar por nome ou matrícula').fill(novoNome);
  await expect(page.getByRole('row').filter({ hasText: novoNome })).toBeVisible();

  page.once('dialog', (confirmacao) => confirmacao.accept());
  await page.getByRole('button', { name: `Inativar ${novoNome}` }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Aluno inativado.' })).toBeVisible();

  const gravado = await admin.get(`/academico/alunos/${c.aluno.id}`);
  expect(gravado.status).toBe('inativo');
  expect(gravado.nome_completo).toBe(novoNome);
  expect(gravado.inscricoes).toHaveLength(1); // o histórico fica
});

test('o professor não vê nem alcança os cadastros', async ({ page }) => {
  const professor = await criarProfessor();

  await iniciarSessao(page, professor.email);
  await expect(menu(page).getByRole('link', { name: 'Cadastros' })).toHaveCount(0);

  await page.goto('/cadastros');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: 'Cadastros' })).toHaveCount(0);
});

test('aluno de uma turma fora das 100 mais recentes continua editável', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);
  // 100 turmas mais novas empurram a turma do aluno para fora das listas de escolha (100 itens).
  for (let i = 0; i < 100; i++) {
    await admin.post('/academico/turmas', {
      nome: `Turma extra ${unico()}`,
      curso: 'Inteligência Artificial',
      periodo_letivo: '2026.2',
      turno: 'noturno',
    });
  }
  const novoNome = `Aluno turma antiga ${unico()}`;

  await iniciarSessao(page, USUARIOS.coordenacao);
  await abrirCadastros(page, 'Alunos');
  await page.getByPlaceholder('Buscar por nome ou matrícula').fill(c.aluno.nome_completo);
  await page.getByRole('button', { name: `Editar ${c.aluno.nome_completo}` }).click();

  const form = page.getByRole('dialog', { name: 'Editar aluno' });
  const turma = form.getByRole('combobox', { name: 'Turma' });
  await expect(turma).toHaveValue(String(c.turma.id)); // a turma atual está na lista, mesmo fora das 100
  await expect(turma.locator('option:checked')).toHaveText(c.turma.nome); // com o nome, não "Turma 123"
  await form.getByRole('textbox', { name: 'Nome completo' }).fill(novoNome);
  await form.getByRole('button', { name: 'Salvar alterações' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Alterações salvas.' })).toBeVisible();

  const gravado = await admin.get(`/academico/alunos/${c.aluno.id}`);
  expect(gravado.nome_completo).toBe(novoNome);
  expect(gravado.turma_id).toBe(c.turma.id);
});
