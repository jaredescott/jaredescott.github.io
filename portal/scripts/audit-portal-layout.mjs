import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const url = process.env.PORTAL_URL ?? 'http://localhost:4173/portal/preview.html';
const outDir = path.join(__dirname, '..', 'assets');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(url, { waitUntil: 'networkidle', timeout: 30_000 });
await page.waitForTimeout(1500);

const metrics = await page.evaluate(() => {
  const slots = [...document.querySelectorAll('[data-portal-slot]')].map((el) => {
    const r = el.getBoundingClientRect();
    return { id: el.dataset.portalSlot, x: r.x, y: r.y, w: r.width, h: r.height };
  });
  const row = document.querySelector('.portal-row')?.getBoundingClientRect();
  return { slots, row, dpr: window.devicePixelRatio };
});

console.log(JSON.stringify(metrics, null, 2));
await page.screenshot({ path: path.join(outDir, '_audit-portal.png'), fullPage: false });
console.log('screenshot: assets/_audit-portal.png');
await browser.close();
