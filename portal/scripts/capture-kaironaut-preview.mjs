import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { seedKaironautPageStorage } from '../../../kaironaut/scripts/demo-persist.mjs';
import { recordViewportGif } from './gif-utils.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outFile = path.join(__dirname, '..', 'assets', 'kaironaut-preview.gif');
const baseUrl = process.env.KAIRONAUT_URL ?? 'https://jaredescott.github.io/kaironaut/';

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});

await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60_000 });
await seedKaironautPageStorage(page);
await page.reload({ waitUntil: 'networkidle', timeout: 60_000 });
await page.waitForTimeout(800);

const localBtn = page.getByRole('button', { name: 'Continue without sign-in' });
if (await localBtn.isVisible({ timeout: 8000 }).catch(() => false)) {
  await localBtn.click();
  await page.waitForTimeout(2000);
}

await page.locator('nav[aria-label="Main"]').waitFor({ state: 'visible', timeout: 15_000 });
const nav = page.locator('nav[aria-label="Main"]');
const navChild = (label) => nav.locator(`button[title="${label}"]`).first();
const recalc = page.getByRole('button', { name: 'Recalculate schedule' });

async function openChronolabe() {
  if (await page.locator('.chronolabe-wrap').isVisible().catch(() => false)) {
    return;
  }
  await nav.locator('button.nav-btn-group-parent').click();
  await page.locator('.chronolabe-wrap').waitFor({ state: 'visible', timeout: 10_000 });
  await page.waitForTimeout(500);
}

async function runRecalculate() {
  if (await recalc.isVisible({ timeout: 3000 }).catch(() => false)) {
    await recalc.click();
    await page.waitForTimeout(4500);
  }
}

async function segmentCount() {
  return page.locator('.chronolabe-segment:not(.is-dragging)').count();
}

async function goToToday() {
  for (let i = 0; i < 16; i += 1) {
    const label = await page.locator('.chronolabe-day-label').textContent().catch(() => '');
    if (label?.includes('Today')) return;
    await page.getByRole('button', { name: 'Previous day' }).click();
    await page.waitForTimeout(150);
  }
}

async function focusBusiestChronolabeDay() {
  await openChronolabe();
  await runRecalculate();
  await goToToday();

  let bestCount = -1;
  let bestStep = 0;
  for (let step = 0; step <= 12; step += 1) {
    const count = await segmentCount();
    if (count > bestCount) {
      bestCount = count;
      bestStep = step;
    }
    if (step < 12) {
      await page.getByRole('button', { name: 'Next day' }).click();
      await page.waitForTimeout(300);
    }
  }

  for (let i = 12; i > bestStep; i -= 1) {
    await page.getByRole('button', { name: 'Previous day' }).click();
    await page.waitForTimeout(150);
  }

  console.log(`chronolabe segments on best day: ${bestCount}`);
}

await focusBusiestChronolabeDay();

await recordViewportGif(page, outFile, async (add) => {
  await add(1400);
  await add(1400);

  await navChild('Calendar').click();
  await page.waitForTimeout(900);
  await runRecalculate();
  await add(1400);
  await add(1400);

  await openChronolabe();
  await focusBusiestChronolabeDay();
  await add(1400);
  await add(1400);
});

await browser.close();
