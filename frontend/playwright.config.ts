import { defineConfig, devices } from '@playwright/test';

// Testes de navegador contra o ambiente ISOLADO `simpa-test` (compose.test.yml na raiz do repositório):
// serviços reais atrás do gateway, sem mocks. Suba o ambiente antes (veja tests/e2e/README.md).
const BASE_URL = process.env.SIMPA_BASE_URL ?? 'http://127.0.0.1:18080';

export default defineConfig({
  testDir: './tests/e2e',
  // Cada teste cria os próprios dados pela API e usa uma sessão de navegador nova. Os testes não
  // dependem da ordem; um trabalhador só deixa o diagnóstico mais simples.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  outputDir: 'test-results',
  use: {
    baseURL: BASE_URL,
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    // Trace e captura só quando o teste falha. Eles podem conter o token do ambiente de teste
    // (sintético e de curta duração): não os publique fora do CI privado.
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
