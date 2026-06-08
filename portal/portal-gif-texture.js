import * as THREE from 'three';
import { parseGIF, decompressFrames } from 'gifuct-js';

function drawGifFrame(player, index) {
  const { ctx, canvas, frames, imageData } = player;
  const frame = frames[index];
  const { left, top } = frame.dims;

  if (frame.disposalType === 2) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (player.bitmap) {
      ctx.putImageData(player.bitmap, 0, 0);
    }
  }

  imageData.data.set(frame.patch);
  ctx.putImageData(imageData, left, top);
  player.bitmap = ctx.getImageData(0, 0, canvas.width, canvas.height);
  player.tex.needsUpdate = true;
}

export async function loadGifTexture(url) {
  const response = await fetch(url);
  if (!response.ok) return null;

  const buffer = await response.arrayBuffer();
  const gif = parseGIF(buffer);
  const frames = decompressFrames(gif, true);
  if (!frames.length) return null;

  const canvas = document.createElement('canvas');
  canvas.width = gif.lsd.width;
  canvas.height = gif.lsd.height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const imageData = ctx.createImageData(canvas.width, canvas.height);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;

  const player = {
    tex,
    aspect: canvas.width / canvas.height,
    frames,
    canvas,
    ctx,
    imageData,
    bitmap: null,
    frameIndex: 0,
    elapsed: 0,
  };

  drawGifFrame(player, 0);
  return player;
}

export function tickGifTexture(player, deltaMs) {
  if (!player?.frames?.length) return;
  player.elapsed += deltaMs;
  const delay = player.frames[player.frameIndex]?.delay ?? 100;
  if (player.elapsed < delay) return;
  player.elapsed -= delay;
  player.frameIndex = (player.frameIndex + 1) % player.frames.length;
  drawGifFrame(player, player.frameIndex);
}
