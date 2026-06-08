import gifencPkg from 'gifenc';
import pngjsPkg from 'pngjs';
import fs from 'node:fs';

const { GIFEncoder, quantize, applyPalette } = gifencPkg;
const { PNG } = pngjsPkg;

/** @typedef {{ data: Uint8Array; width: number; height: number }} GifFrame */

/** @param {GifFrame[]} frames @param {number[]} delaysMs */
export function encodeGif(frames, delaysMs) {
  const { width, height } = frames[0];
  const enc = GIFEncoder();
  for (let i = 0; i < frames.length; i++) {
    const rgba = frames[i].data;
    const palette = quantize(rgba, 256);
    const index = applyPalette(rgba, palette);
    enc.writeFrame(index, width, height, {
      palette,
      delay: delaysMs[i] ?? 400,
    });
  }
  enc.finish();
  return Buffer.from(enc.bytes());
}

/**
 * @param {import('playwright').Page} page
 * @param {string} outFile
 * @param {(add: (delayMs?: number) => Promise<void>) => Promise<void>} record
 */
export async function recordViewportGif(page, outFile, record) {
  /** @type {GifFrame[]} */
  const frames = [];
  /** @type {number[]} */
  const delays = [];

  const add = async (delayMs = 450) => {
    const buf = await page.screenshot({ type: 'png' });
    const png = PNG.sync.read(buf);
    frames.push({ data: png.data, width: png.width, height: png.height });
    delays.push(delayMs);
  };

  await record(add);
  if (frames.length < 2) {
    throw new Error(`GIF needs at least 2 frames, got ${frames.length}`);
  }
  fs.writeFileSync(outFile, encodeGif(frames, delays));
  console.log(`wrote ${outFile} (${frames.length} frames)`);
}
