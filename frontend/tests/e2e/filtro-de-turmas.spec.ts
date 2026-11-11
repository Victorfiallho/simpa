import { expect, test } from '@playwright/test';
import { entrarNaApi, iniciarSessao, unico } from './suporte';

// O filtro global do cabeçalho já mostrou só as 100 primeiras turmas, sem aviso. Aqui há mais de
// 100: uma turma que ordena por último precisa aparecer na lista.
test('o filtro de turmas lista também as turmas além da centésima', async ({ page }) => {
  test.setTimeout(180_000);
  const admin = await entrarNaApi('admin@simpa.dev');
  const sufixo = unico();
  const ultimo = `ZZ filtro ${sufixo} zzz`;
  for (let lote = 0; lote < 11; lote += 1) {
    await Promise.all(
      Array.from({ length: 10 }, (_, i) => {
        const n = lote * 10 + i;
        return admin.post('/academico/turmas', {
          nome: n === 109 ? ultimo : `ZZ filtro ${sufixo} ${String(n).padStart(3, '0')}`,
          curso: 'Inteligência Artificial',
          periodo_letivo: '2026.2',
          turno: 'noturno',
        });
      }),
    );
  }

  await iniciarSessao(page, 'admin@simpa.dev');
  await page.goto('/alunos');
  const seletor = page.getByRole('combobox', { name: 'Turma', exact: true });
  await expect(seletor.locator('option', { hasText: ultimo })).toHaveCount(1);
  // Nenhuma turma ficou de fora: não há aviso de omissão.
  await expect(page.getByRole('status').filter({ hasText: 'não aparecem' })).toHaveCount(0);
});
