import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outFile = path.join(__dirname, '..', 'assets', 'kaironaut-chronolabe.png');
const baseUrl = process.env.KAIRONAUT_URL ?? 'https://jaredescott.github.io/kaironaut/';

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});

await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 60_000 });
await page.waitForTimeout(800);

const localBtn = page.getByRole('button', { name: 'Continue without sign-in' });
if (await localBtn.isVisible({ timeout: 8000 }).catch(() => false)) {
  await localBtn.click();
  await page.waitForTimeout(2000);
}

await page.locator('nav[aria-label="Main"] button').filter({ hasText: 'Chronolabe' }).first().click();
await page.waitForTimeout(1200);

await page.evaluate(() => {
  const shell = document.querySelector('.app-shell');
  if (shell) {
    shell.classList.add('sidebar-desktop-collapsed');
  }
  document.querySelector('.page-header')?.remove();
});

const recalc = page.getByRole('button', { name: /Recalculate schedule/i });
if (await recalc.isVisible({ timeout: 5000 }).catch(() => false)) {
  await recalc.click();
  await page.waitForTimeout(4000);
}

await page.locator('.chronolabe-wrap').waitFor({ state: 'visible', timeout: 10_000 });
await page.waitForSelector('.chronolabe-segment', { timeout: 8000 }).catch(() => {});

const wrap = page.locator('.chronolabe-wrap');
await wrap.scrollIntoViewIfNeeded();
await page.waitForTimeout(400);
await wrap.screenshot({ path: outFile });

console.log(`wrote ${outFile}`);
await browser.close();
