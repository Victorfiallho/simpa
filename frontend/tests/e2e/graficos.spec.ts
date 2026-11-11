import { expect, test, type Locator, type Page } from '@playwright/test';

import { type Api, criarAluno, criarCenario, criarProfessor, entrarNaApi, iniciarSessao, inscrever, menu, USUARIOS } from './suporte';

// RF06: os gráficos aparecem com título, eixos, legenda e texto explicativo, e mostram os dados do
// banco. Cada teste cria uma turma só dele, com dois alunos de notas conhecidas, e filtra a tela
// por ela. Assim os números esperados são exatos e não dependem do que os outros testes criaram:
//   aluno A: N1 4,00 e frequência 93,75% → Em risco (média abaixo de 6,00)
//   aluno B: N1 8,00 e frequência 93,75% → Sem risco
// Média das duas inscrições 6,00, mediana 6,00, menor 4,00, maior 8,00.

async function lancarN1(admin: Api, inscricaoId: number, nota: string): Promise<void> {
  await admin.post('/academico/avaliacoes', {
    inscricao_id: inscricaoId,
    tipo_avaliacao: 'prova',
    periodo_avaliacao: 'N1',
    nota,
    peso: '4',
  });
  await admin.post('/academico/frequencias', {
    inscricao_id: inscricaoId,
    periodo_avaliacao: 'N1',
    aulas_previstas: 32,
    faltas: 2,
  });
}

async function turmaComDoisAlunos() {
  const admin = await entrarNaApi(USUARIOS.admin);
  const professor = await criarProfessor();
  const c = await criarCenario(admin, professor.api.usuarioId);
  const outro = await criarAluno(admin, c.turma.id);
  const inscricaoOutro = await inscrever(admin, outro.id, c.disciplina.id);
  await lancarN1(admin, c.inscricao.id, '4.00');
  await lancarN1(admin, inscricaoOutro.id, '8.00');
  return c;
}

async function filtrarTurma(page: Page, nome: string): Promise<void> {
  await page.getByRole('combobox', { name: 'Turma', exact: true }).selectOption({ label: nome });
}

/** O cartão (a caixa do gráfico) cujo título é `titulo`. */
function cartao(page: Page, titulo: string): Locator {
  return page
    .getByRole('heading', { name: titulo, exact: true })
    .locator('xpath=ancestor::*[contains(concat(" ", normalize-space(@class), " "), " cartao ")][1]');
}

/** Rótulos dos eixos que o Recharts desenhou dentro do gráfico. */
function rotulosDosEixos(grafico: Locator): Locator {
  return grafico.locator('.recharts-cartesian-axis-tick-value');
}

test('Visão geral: os gráficos mostram os dados da turma, com título, eixos e legenda (RF06)', async ({ page }) => {
  const c = await turmaComDoisAlunos();

  await iniciarSessao(page, USUARIOS.coordenacao);
  await filtrarTurma(page, c.turma.nome);

  const indicadores = page.getByRole('region', { name: 'Indicadores gerais' });
  await expect(indicadores).toContainText('Alunos acompanhados');
  await expect(indicadores.locator('.kpi').first().locator('.kpi-valor')).toHaveText('2');
  await expect(indicadores).toContainText('Média geral');
  await expect(indicadores).toContainText('6,00');

  // Histograma: título, explicação, eixo com as faixas de média e a nota de leitura.
  const histograma = cartao(page, 'Distribuição das médias');
  await expect(histograma).toContainText('Inscrições por faixa de média final (0 a 10)');
  await expect(histograma.locator('svg.recharts-surface')).toBeVisible();
  await expect(rotulosDosEixos(histograma).filter({ hasText: '4–5' })).toHaveCount(1);
  await expect(rotulosDosEixos(histograma).filter({ hasText: '8–9' })).toHaveCount(1);
  await expect(histograma).toContainText('Abaixo de 6,00 a inscrição está em risco por média.');

  // Dispersão: um ponto por inscrição, eixos de frequência (%) e média, linhas de referência.
  const dispersao = cartao(page, 'Frequência × média');
  await expect(dispersao).toContainText('Cada ponto é uma inscrição');
  await expect(dispersao.locator('.recharts-scatter-symbol')).toHaveCount(2);
  await expect(rotulosDosEixos(dispersao).filter({ hasText: '100%' })).toHaveCount(1);
  await expect(dispersao).toContainText('Linhas tracejadas: 75% e 6,00.');

  // Barras por disciplina e turma: legenda com as quatro situações escritas.
  const porOferta = cartao(page, 'Inscrições por disciplina e turma');
  await expect(porOferta.locator('svg.recharts-surface')).toBeVisible();
  for (const situacao of ['Sem risco', 'Atenção', 'Indeterminado', 'Em risco']) {
    await expect(porOferta.locator('.legenda')).toContainText(situacao);
  }

  // Anéis de situação: metade dos alunos em cada lado, com o número escrito.
  for (const situacao of ['Em risco', 'Sem risco']) {
    const bloco = page.locator('.bloco').filter({ has: page.getByRole('heading', { name: situacao, exact: true }) });
    await expect(bloco.getByRole('img', { name: '50% dos alunos' })).toBeVisible();
    await expect(bloco.locator('.bloco-rodape')).toHaveText('1 aluno');
  }
  for (const situacao of ['Atenção', 'Indeterminado']) {
    const bloco = page.locator('.bloco').filter({ has: page.getByRole('heading', { name: situacao, exact: true }) });
    await expect(bloco.getByRole('img', { name: '0% dos alunos' })).toBeVisible();
  }
});

test('Análises: estatística, ranking e evolução refletem as notas lançadas (RF05, RF06)', async ({ page }) => {
  const c = await turmaComDoisAlunos();

  await iniciarSessao(page, USUARIOS.coordenacao);
  await menu(page).getByRole('link', { name: 'Análises' }).click();
  await filtrarTurma(page, c.turma.nome);

  const estatistica = cartao(page, 'Estatística descritiva das médias');
  await expect(estatistica).toContainText('2 inscrições com dados');
  const valor = (rotulo: string) =>
    estatistica.locator('.estatisticas > div').filter({ has: page.getByText(rotulo, { exact: true }) }).locator('strong');
  await expect(valor('Média')).toHaveText('6,00');
  await expect(valor('Mediana')).toHaveText('6,00');
  await expect(valor('Menor média')).toHaveText('4,00');
  await expect(valor('Maior média')).toHaveText('8,00');

  // Ranking: uma barra (a única disciplina da turma), com a média escrita ao lado.
  const ranking = cartao(page, 'Ranking de disciplinas');
  await expect(ranking.locator('.recharts-bar-rectangle')).toHaveCount(1);
  await expect(ranking.locator('.recharts-label-list')).toContainText('6,00');

  // Evolução: eixo de 0 a 10 e legenda das duas séries.
  const evolucao = cartao(page, 'Evolução por disciplina');
  await expect(evolucao).toContainText('Média só da N1 comparada à média acumulada (N1 + N2)');
  await expect(rotulosDosEixos(evolucao).filter({ hasText: /^10$/ })).toHaveCount(1);
  await expect(evolucao.locator('.legenda')).toContainText('N1');
  await expect(evolucao.locator('.legenda')).toContainText('Acumulado');

  // Situação das inscrições: o número de cada situação aparece escrito junto da barra.
  const situacao = cartao(page, 'Situação das inscrições');
  const linha = (rotulo: string) =>
    situacao.locator('.barras-situacao > div').filter({ has: page.getByText(rotulo, { exact: true }) }).locator('strong');
  await expect(linha('Em risco')).toHaveText('1');
  await expect(linha('Sem risco')).toHaveText('1');
  await expect(linha('Atenção')).toHaveText('0');
});
