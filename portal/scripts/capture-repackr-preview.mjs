import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outFile = path.join(__dirname, '..', 'assets', 'repackr-preview.png');
const baseUrl = process.env.REPACKR_URL ?? 'https://jaredescott.github.io/repackr/';

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 2,
});

await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 60_000 });
await page.evaluate(() => {
  localStorage.setItem('repackr_tutorial_completed', 'true');
});
await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(2000);
await page.getByRole('button', { name: /got it|close|skip|dismiss/i }).click({ timeout: 2000 }).catch(() => {});
await page.waitForTimeout(500);

await page.screenshot({ path: outFile, fullPage: false });

console.log(`wrote ${outFile}`);
await browser.close();
