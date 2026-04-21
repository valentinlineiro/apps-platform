import { chromium, FullConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const AUTH_FILE = path.join(process.cwd(), '.auth/user.json');

async function globalSetup(_config: FullConfig) {
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();

  // Navigate to portal — will redirect to Keycloak login
  await page.goto('https://localhost', { waitUntil: 'networkidle' });

  // Fill Keycloak login form
  await page.fill('#username', process.env['E2E_USERNAME'] ?? 'demo');
  await page.fill('#password', process.env['E2E_PASSWORD'] ?? 'demo123');
  await page.click('[type=submit]');

  // Wait until we're back on the portal (Keycloak redirects to /auth/callback then /)
  await page.waitForURL('https://localhost/**', { waitUntil: 'networkidle' });

  await context.storageState({ path: AUTH_FILE });
  await browser.close();
}

export default globalSetup;
