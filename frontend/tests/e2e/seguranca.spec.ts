import { expect, test } from '@playwright/test';
import { iniciarSessao } from './suporte';

// A CSP não pode quebrar a aplicação: percorre as telas principais logado e falha se o navegador
// bloquear qualquer recurso (script, estilo, fonte, imagem ou conexão) por causa da política.
test('a CSP não bloqueia nada nas telas principais', async ({ page }) => {
  const violacoes: string[] = [];
  await page.addInitScript(() => {
    (window as unknown as { __csp: string[] }).__csp = [];
    document.addEventListener('securitypolicyviolation', (e) => {
      (window as unknown as { __csp: string[] }).__csp.push(`${e.violatedDirective} ${e.blockedURI}`);
    });
  });
  page.on('console', (m) => {
    if (/Content Security Policy|Refused to/i.test(m.text())) violacoes.push(m.text());
  });

  await iniciarSessao(page, 'admin@simpa.dev');
  for (const caminho of ['/', '/alunos', '/analises', '/alertas', '/cenarios', '/cadastros', '/lancamentos', '/copiloto', '/pendencias', '/auditoria', '/relatorios', '/perfil']) {
    await page.goto(caminho);
    await page.waitForLoadState('networkidle');
    const vistas = await page.evaluate(() => (window as unknown as { __csp?: string[] }).__csp ?? []);
    violacoes.push(...vistas.map((v) => `${caminho}: ${v}`));
  }
  expect(violacoes, violacoes.join('\n')).toEqual([]);
});

test('a página responde com a CSP e sem possibilidade de embutir', async ({ request }) => {
  const resposta = await request.get('/');
  const csp = resposta.headers()['content-security-policy'] ?? '';
  expect(csp).toContain("script-src 'self'");
  expect(resposta.headers()['x-frame-options']).toBe('DENY');
});
