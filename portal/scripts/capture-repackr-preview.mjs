import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outFile = path.join(__dirname, '..', 'assets', 'repackr-preview.png');
const baseUrl = process.env.REPACKR_URL ?? 'https://jaredescott.github.io/repackr/';

function seedDailyBoardsScript() {
  localStorage.setItem('repackr_tutorial_completed', 'true');
  const master = JSON.parse(localStorage.getItem('repackr_master_items') ?? '[]');
  if (!master.length) return;

  const clone = (item, quantity = 1) => ({
    id: crypto.randomUUID(),
    name: item.name,
    category: item.category,
    quantity,
    isReusable: item.isReusable,
  });

  const daily = JSON.parse(localStorage.getItem('repackr_daily_boards') ?? '[]');
  if (daily[0]) {
    daily[0].items = [
      clone(master[0], 2),
      clone(master[1], 1),
      clone(master[2], 1),
      clone(master[3], 1),
      clone(master[5], 1),
    ];
  }
  if (daily[1]) {
    daily[1].items = [clone(master[4], 1), clone(master[6], 1)];
  }
  localStorage.setItem('repackr_daily_boards', JSON.stringify(daily));
}

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});

await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 60_000 });
await page.evaluate(seedDailyBoardsScript);
await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(1500);

await page.getByRole('button', { name: /got it|close|skip|dismiss/i }).click({ timeout: 2000 }).catch(() => {});
await page.waitForTimeout(500);

await page.locator('#days-container').waitFor({ state: 'visible', timeout: 10_000 });
await page.getByText('T-Shirt').first().waitFor({ state: 'visible', timeout: 10_000 });
await page.screenshot({ path: outFile, fullPage: false });

console.log(`wrote ${outFile}`);
await browser.close();
