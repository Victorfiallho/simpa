import { expect, type Locator, type Page, test } from '@playwright/test';

import { criarCenario, criarProfessor, criarUsuarioAluno, entrarNaApi, iniciarSessao, menu, unico, USUARIOS } from './suporte';

// RNF11: a interface indica os campos obrigatórios. Em cada formulário, todo campo `required` tem o
// asterisco no rótulo, nenhum campo opcional tem, e a legenda explica o asterisco. Enviar o
// formulário vazio não cadastra nada.

interface CampoDoFormulario {
  rotulo: string;
  obrigatorio: boolean;
  marcado: boolean;
}

async function camposDo(formulario: Locator): Promise<CampoDoFormulario[]> {
  return formulario.evaluate((form) =>
    Array.from(form.querySelectorAll<HTMLInputElement>('input, select, textarea'))
      .filter((campo) => campo.type !== 'hidden')
      .map((campo) => {
        const rotulo = campo.closest('label');
        // Só o texto do rótulo: o `textContent` do label inteiro traria também as opções do select.
        const texto = rotulo?.querySelector('span')?.textContent ?? rotulo?.childNodes[0]?.textContent ?? campo.name;
        return {
          rotulo: texto.replace('*', '').trim(),
          obrigatorio: campo.required,
          marcado: Boolean(rotulo?.querySelector('.obrigatorio')),
        };
      }),
  );
}

async function conferirIndicacao(formulario: Locator): Promise<void> {
  const campos = await camposDo(formulario);
  expect(campos.filter((c) => c.obrigatorio).length, 'o formulário tem campos obrigatórios').toBeGreaterThan(0);
  const divergentes = campos.filter((c) => c.obrigatorio !== c.marcado).map((c) => c.rotulo);
  expect(divergentes, 'campos com asterisco e campos obrigatórios são os mesmos').toEqual([]);
  await expect(formulario.locator('.legenda-obrigatorios')).toHaveText('Campos com * são obrigatórios.');
}

async function abrirCadastros(page: Page, aba: 'Turmas' | 'Disciplinas' | 'Alunos' | 'Inscrições') {
  await menu(page).getByRole('link', { name: 'Cadastros' }).click();
  await page.getByRole('group', { name: 'Tipo de cadastro' }).getByRole('button', { name: aba }).click();
}

for (const [aba, botao] of [
  ['Turmas', 'Nova turma'],
  ['Disciplinas', 'Nova disciplina'],
  ['Alunos', 'Novo aluno'],
] as const) {
  test(`${botao}: os campos obrigatórios estão indicados e o envio vazio não cadastra`, async ({ page }) => {
    await iniciarSessao(page, USUARIOS.coordenacao);
    await abrirCadastros(page, aba);
    await page.getByRole('button', { name: botao }).click();
    const dialogo = page.getByRole('dialog', { name: botao });
    const formulario = dialogo.locator('form');

    await conferirIndicacao(formulario);

    let enviou = false;
    page.on('request', (r) => {
      if (r.method() === 'POST' && r.url().includes('/api/academico/')) enviou = true;
    });
    await dialogo.getByRole('button', { name: 'Cadastrar' }).click();
    // O navegador barra o envio e aponta o primeiro campo vazio; o formulário continua aberto.
    await expect(dialogo).toBeVisible();
    expect(await formulario.locator(':invalid').count()).toBeGreaterThan(0);
    expect(enviou, 'nenhum POST sai com o formulário vazio').toBe(false);
  });
}

test('Inscrições: a matrícula do aluno está indicada como obrigatória', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const sufixo = unico();
  const turma = await admin.post('/academico/turmas', {
    nome: `Turma obrigatorios ${sufixo}`,
    curso: 'Inteligência Artificial',
    periodo_letivo: '2026.2',
    turno: 'noturno',
  });
  // A lista de disciplinas da aba vem ordenada por nome e cortada em 100: um nome que começa
  // com "A" fica no começo dela.
  const disciplina = `A obrigatorios ${sufixo}`;
  await admin.post('/academico/disciplinas', {
    nome: disciplina,
    carga_horaria: 60,
    periodo_letivo: '2026.2',
    turma_id: turma.id,
    professor_id: professor.api.usuarioId,
  });

  await iniciarSessao(page, USUARIOS.coordenacao);
  await abrirCadastros(page, 'Inscrições');
  await page.getByRole('combobox', { name: 'Disciplina', exact: true }).selectOption({ label: `${disciplina} · ${turma.nome}` });
  const formulario = page.locator('form.parametros');
  const campos = await camposDo(formulario);
  expect(campos).toEqual([{ rotulo: 'Matrícula do aluno', obrigatorio: true, marcado: true }]);
});

test('Pedir apoio: o texto do pedido está indicado como obrigatório', async ({ page }) => {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);
  criarUsuarioAluno(c.aluno.id, c.aluno.email);

  await iniciarSessao(page, c.aluno.email);
  await menu(page).getByRole('link', { name: 'Pedir apoio' }).click();
  const formulario = page.locator('form').filter({ has: page.getByRole('button', { name: 'Enviar pedido' }) });

  await conferirIndicacao(formulario);
  // O asterisco é só visual: o nome acessível do campo continua sendo o rótulo.
  await expect(page.getByRole('textbox', { name: 'Conte o que está acontecendo', exact: true })).toBeVisible();
});
