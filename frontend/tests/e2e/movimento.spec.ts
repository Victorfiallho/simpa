import { expect, type Page, test } from '@playwright/test';

import { iniciarSessao, menu, USUARIOS } from './suporte';

// Movimento da interface (src/movimento.ts e o fim de global.css). Os demais testes rodam com
// prefers-reduced-motion: reduce (playwright.config.ts); aqui se confere que essa preferência é
// respeitada e que, sem ela, as animações acontecem e terminam no estado certo.

/** Animações CSS que ainda vão durar mais de 1 ms. */
async function animacoesLongas(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    document
      .getAnimations()
      .filter((a) => {
        const fim = Number(a.effect?.getComputedTiming().endTime ?? 0);
        return a.playState !== 'finished' && fim > 1;
      })
      .map((a) => (a as CSSAnimation).animationName ?? 'js'),
  );
}

test('com movimento reduzido, as telas e o menu já aparecem no estado final', async ({ page }) => {
  await iniciarSessao(page, USUARIOS.coordenacao);
  await expect(page.locator('.transicao .cartao').first()).toBeVisible();
  expect(await animacoesLongas(page)).toEqual([]);

  await menu(page).getByRole('link', { name: 'Alunos' }).click();
  const indicador = page.locator('.icone-ativo');
  await expect(indicador).toHaveCount(1);
  // Sem deslizar: o indicador já está no item novo, sem deslocamento.
  expect(await indicador.evaluate((i) => [i.closest('a')?.textContent, getComputedStyle(i).transform])).toEqual([
    'Alunos',
    'none',
  ]);
});

test.describe('sem preferência de movimento', () => {
  test.use({ contextOptions: { reducedMotion: 'no-preference' } });

  test('os cartões entram em sequência e terminam visíveis, sem deslocamento', async ({ page }) => {
    await iniciarSessao(page, USUARIOS.coordenacao);
    const cartoes = page.locator('.transicao .cartao');
    await expect(cartoes.first()).toBeVisible();
    expect(await cartoes.first().evaluate((c) => getComputedStyle(c).animationName)).toBe('surgir');

    await expect
      .poll(() => cartoes.evaluateAll((lista) => lista.every((c) => getComputedStyle(c).opacity === '1')))
      .toBe(true);
    // A camada de transição não pode deixar transform: ele prenderia as gavetas (position: fixed).
    await expect.poll(() => page.locator('.transicao').evaluate((t) => getComputedStyle(t).transform)).toBe('none');
  });

  test('o indicador do menu desliza até o item escolhido e assenta', async ({ page }) => {
    await iniciarSessao(page, USUARIOS.coordenacao);
    await menu(page).getByRole('link', { name: 'Análises' }).click();
    const indicador = page.locator('.icone-ativo');

    await expect(indicador).toHaveCount(1);
    expect(await indicador.evaluate((i) => i.closest('a')?.textContent)).toBe('Análises');
    await expect.poll(() => indicador.evaluate((i) => getComputedStyle(i).transform)).toBe('none');
  });
});
