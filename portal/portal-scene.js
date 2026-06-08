import * as THREE from 'three';
import { loadGifTexture, tickGifTexture } from './portal-gif-texture.js';

const BG_Z = -5.5;
const BG_SIZE = { w: 22, h: 14, y: 0.2 };

const PORTAL_VERT = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const PORTAL_PREVIEW_FRAG = `
  uniform sampler2D uTexture;
  uniform float uHover;
  uniform float uReady;
  uniform float uBrightness;
  uniform float uTexAspect;
  uniform float uPortalAspect;
  uniform float uShape;
  varying vec2 vUv;

  vec2 fitContain(vec2 uv) {
    vec2 c = uv - 0.5;
    vec2 scale = (uTexAspect > uPortalAspect)
      ? vec2(1.0, uPortalAspect / uTexAspect)
      : vec2(uTexAspect / uPortalAspect, 1.0);
    return c / scale + 0.5;
  }

  float rectMask(vec2 uv) {
    vec2 d = abs(uv - 0.5) - vec2(0.485, 0.485);
    float round = 0.032;
    float dist = length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - round;
    return 1.0 - smoothstep(-0.008, 0.015, dist);
  }

  float circleMask(vec2 uv) {
    float dist = length(uv - 0.5);
    return smoothstep(0.502, 0.478, dist);
  }

  void main() {
    vec2 sampleUv = (uShape > 0.5) ? fitContain(vUv) : vUv;
    float inBounds = step(0.001, sampleUv.x) * step(sampleUv.x, 0.999)
      * step(0.001, sampleUv.y) * step(sampleUv.y, 0.999);
    vec3 col = texture2D(uTexture, clamp(sampleUv, 0.001, 0.999)).rgb * uBrightness;
    col = mix(vec3(0.04, 0.08, 0.16), col, inBounds);

    float mask = mix(rectMask(vUv), circleMask(vUv), uShape);
    float rim = mask * (0.1 + uHover * 0.08);
    col += vec3(0.38, 0.58, 0.96) * rim;

    gl_FragColor = vec4(col, mask * uReady);
  }
`;

const BG_VERT = `
  varying vec2 vWorldXY;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorldXY = world.xy;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const BG_LENS_FRAG = `
  uniform sampler2D uBg;
  uniform vec2 uPortal0;
  uniform vec2 uPortal1;
  uniform vec2 uRadius0;
  uniform vec2 uRadius1;
  uniform float uStrength;
  uniform float uOpacity;
  varying vec2 vWorldXY;

  vec2 lensWorld(vec2 xy, vec2 portal, vec2 radius) {
    vec2 d = xy - portal;
    vec2 n = d / max(radius, vec2(0.001));
    float r = length(n);
    if (r < 0.001) return xy;
    float bend = smoothstep(1.55, 0.12, r) * uStrength;
    return xy + normalize(d) * bend * min(r * 0.85, 1.0);
  }

  void main() {
    vec2 warped = vWorldXY;
    warped = lensWorld(warped, uPortal0, uRadius0);
    warped = lensWorld(warped, uPortal1, uRadius1);

    vec2 texUV = vec2(
      warped.x / ${BG_SIZE.w.toFixed(1)} + 0.5,
      (warped.y - ${BG_SIZE.y.toFixed(1)}) / ${BG_SIZE.h.toFixed(1)} + 0.5
    );
    texUV = clamp(texUV, 0.001, 0.999);
    vec3 col = texture2D(uBg, texUV).rgb;
    gl_FragColor = vec4(col, uOpacity);
  }
`;

const PORTALS = [
  {
    id: 'repackr',
    href: '/repackr/',
    texture: 'assets/repackr-preview.png',
    accent: 0x2563eb,
    shape: 'rect',
    brightness: 0.88,
  },
  {
    id: 'kaironaut',
    href: '/kaironaut/',
    texture: 'assets/kaironaut-preview.gif',
    accent: 0x93c5fd,
    shape: 'rect',
    brightness: 1.0,
    animated: true,
  },
];

const LENS_SLOTS = [
  { id: 'repackr', shape: 'rect', lensScale: 0.94 },
  { id: 'kaironaut', shape: 'rect', lensScale: 0.94 },
];

const canvas = document.getElementById('portal-canvas');
const loader = new THREE.TextureLoader();
const clock = new THREE.Clock();
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const planeHit = new THREE.Vector3();
const scratch = new THREE.Vector3();

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x0a1628, 0.032);

const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 0, 7.5);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x050a14);

scene.add(new THREE.AmbientLight(0x7eb8ff, 0.35));

const bgUniforms = {
  uBg: { value: null },
  uPortal0: { value: new THREE.Vector2(-2.2, 0) },
  uPortal1: { value: new THREE.Vector2(2.2, 0) },
  uRadius0: { value: new THREE.Vector2(1.05, 1.05) },
  uRadius1: { value: new THREE.Vector2(1.2, 0.9) },
  uStrength: { value: 0.32 },
  uOpacity: { value: 0.5 },
};

loader.load('assets/arcadian-bg.jpg', (bgTex) => {
  bgTex.colorSpace = THREE.SRGBColorSpace;
  bgTex.minFilter = THREE.LinearFilter;
  bgUniforms.uBg.value = bgTex;

  const bg = new THREE.Mesh(
    new THREE.PlaneGeometry(BG_SIZE.w, BG_SIZE.h),
    new THREE.ShaderMaterial({
      uniforms: bgUniforms,
      vertexShader: BG_VERT,
      fragmentShader: BG_LENS_FRAG,
      transparent: true,
      depthWrite: false,
    }),
  );
  bg.position.set(0, BG_SIZE.y, BG_Z);
  scene.add(bg);
});

function createSpriteTexture() {
  const size = 64;
  const c = document.createElement('canvas');
  c.width = size;
  c.height = size;
  const ctx = c.getContext('2d');
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, 'rgba(255,255,255,0.95)');
  gradient.addColorStop(0.35, 'rgba(147,197,253,0.55)');
  gradient.addColorStop(1, 'rgba(37,99,235,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

const spriteTex = createSpriteTexture();
const particleCount = 380;
const particleGeo = new THREE.BufferGeometry();
const positions = new Float32Array(particleCount * 3);
const colors = new Float32Array(particleCount * 3);
const indigo = new THREE.Color(0x93c5fd);
const white = new THREE.Color(0xffffff);
for (let i = 0; i < particleCount; i += 1) {
  positions[i * 3] = (Math.random() - 0.5) * 18;
  positions[i * 3 + 1] = Math.random() * 6 - 1;
  positions[i * 3 + 2] = (Math.random() - 0.5) * 8 - 2;
  const mix = Math.random();
  const c = white.clone().lerp(indigo, mix * 0.7);
  colors[i * 3] = c.r;
  colors[i * 3 + 1] = c.g;
  colors[i * 3 + 2] = c.b;
}
particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
const particles = new THREE.Points(
  particleGeo,
  new THREE.PointsMaterial({
    map: spriteTex,
    size: 0.12,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.75,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexColors: true,
  }),
);
scene.add(particles);

const portalMeshes = [];
const portalGroups = [];
const gifPlayers = [];

function loadPreviewTexture(url) {
  return new Promise((resolve) => {
    loader.load(
      url,
      (tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        tex.wrapS = THREE.ClampToEdgeWrapping;
        tex.wrapT = THREE.ClampToEdgeWrapping;
        const aspect = tex.image ? tex.image.width / tex.image.height : 1;
        resolve({ tex, aspect });
      },
      undefined,
      () => resolve(null),
    );
  });
}

async function buildPortal(config) {
  const group = new THREE.Group();
  let texture = null;
  let texAspect = 16 / 10;
  let gifPlayer = null;

  if (config.animated) {
    gifPlayer = await loadGifTexture(config.texture);
    if (gifPlayer) {
      texture = gifPlayer.tex;
      texAspect = gifPlayer.aspect;
      gifPlayers.push(gifPlayer);
    }
  }

  if (!texture) {
    const loaded = await loadPreviewTexture(config.texture);
    texture = loaded?.tex ?? null;
    texAspect = loaded?.aspect ?? texAspect;
  }

  const portalAspect = config.portalAspect ?? texAspect;

  const portalMat = new THREE.ShaderMaterial({
    uniforms: {
      uTexture: { value: texture ?? new THREE.Texture() },
      uHover: { value: 0 },
      uReady: { value: texture ? 1 : 0 },
      uBrightness: { value: config.brightness ?? 1.0 },
      uTexAspect: { value: texAspect },
      uPortalAspect: { value: portalAspect },
      uShape: { value: config.shape === 'circle' ? 1 : 0 },
    },
    vertexShader: PORTAL_VERT,
    fragmentShader: PORTAL_PREVIEW_FRAG,
    transparent: true,
    depthWrite: false,
  });

  const geometry = config.shape === 'circle'
    ? new THREE.CircleGeometry(1, 96)
    : new THREE.PlaneGeometry(1, 1);

  const portal = new THREE.Mesh(geometry, portalMat);
  portal.userData = { href: config.href, id: config.id, type: 'portal', shape: config.shape };
  group.add(portal);

  const glowScale = config.shape === 'circle' ? 1.04 : 1.05;
  const glowGeometry = config.shape === 'circle'
    ? new THREE.CircleGeometry(glowScale, 64)
    : new THREE.PlaneGeometry(glowScale, glowScale * (1 / portalAspect));

  const glow = new THREE.Mesh(
    glowGeometry,
    new THREE.MeshBasicMaterial({
      color: config.accent,
      transparent: true,
      opacity: config.featured ? 0.12 : 0.07,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  glow.position.z = -0.02;
  group.add(glow);

  scene.add(group);
  portalGroups.push({ group, portal, glow, config });
  portalMeshes.push(portal);
}

await Promise.all(PORTALS.map(buildPortal));

let hoveredPortal = null;

function setHoveredPortal(portal) {
  if (hoveredPortal === portal) return;
  hoveredPortal = portal;
  document.body.classList.toggle('portal-hover', Boolean(portal));
}

function pickPortal(clientX, clientY) {
  pointer.x = (clientX / window.innerWidth) * 2 - 1;
  pointer.y = -(clientY / window.innerHeight) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(portalMeshes, false);
  return hits[0]?.object ?? null;
}

canvas.addEventListener('pointermove', (event) => {
  const hit = pickPortal(event.clientX, event.clientY);
  setHoveredPortal(hit);
  canvas.style.cursor = hit ? 'pointer' : 'default';
});

canvas.addEventListener('pointerleave', () => {
  setHoveredPortal(null);
  canvas.style.cursor = 'default';
});

canvas.addEventListener('click', (event) => {
  const hit = pickPortal(event.clientX, event.clientY);
  if (hit?.userData.href) window.location.href = hit.userData.href;
});

function screenToWorldOnZ(x, y, z, target) {
  const ndc = new THREE.Vector3(
    (x / window.innerWidth) * 2 - 1,
    -(y / window.innerHeight) * 2 + 1,
    0.5,
  );
  ndc.unproject(camera);
  const dir = ndc.sub(camera.position).normalize();
  const distance = (z - camera.position.z) / dir.z;
  target.copy(camera.position).add(dir.multiplyScalar(distance));
  return target;
}

function slotWorldMetrics(rect, z = 0) {
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  screenToWorldOnZ(cx, cy, z, planeHit);

  const right = screenToWorldOnZ(rect.right, cy, z, scratch);
  const bottom = screenToWorldOnZ(cx, rect.bottom, z, new THREE.Vector3());
  const rx = Math.abs(right.x - planeHit.x);
  const ry = Math.abs(bottom.y - planeHit.y);

  return { cx, cy, x: planeHit.x, y: planeHit.y, rx, ry };
}

function alignGroupToSlot(group, rect, config) {
  const metrics = slotWorldMetrics(rect, 0);
  group.position.set(metrics.x, metrics.y, 0);

  const hover = hoveredPortal?.userData.id === config.id ? 1.03 : 1;
  if (config.shape === 'rect') {
    group.scale.set(metrics.rx * 2 * hover, metrics.ry * 2 * hover, 1);
  } else {
    const r = Math.max(metrics.rx, metrics.ry) * hover;
    group.scale.set(r, r, 1);
  }

  return metrics;
}

function updateBackgroundLens() {
  LENS_SLOTS.forEach((slot, index) => {
    const el = document.querySelector(`[data-portal-slot="${slot.id}"]`);
    if (!el) return;

    const metrics = slotWorldMetrics(el.getBoundingClientRect(), BG_Z);
    bgUniforms[`uPortal${index}`].value.set(metrics.x, metrics.y);

    const scale = slot.lensScale ?? 1.0;
    if (slot.shape === 'rect') {
      bgUniforms[`uRadius${index}`].value.set(metrics.rx * scale, metrics.ry * scale);
    } else {
      const r = Math.max(metrics.rx, metrics.ry) * scale;
      bgUniforms[`uRadius${index}`].value.set(r, r);
    }

    if (index === 0) {
      bgUniforms.uStrength.value = 0.34;
    }
  });
}

function alignPortalsToSlots() {
  portalGroups.forEach(({ group, config }) => {
    const slot = document.querySelector(`[data-portal-slot="${config.id}"]`);
    if (!slot) return;
    alignGroupToSlot(group, slot.getBoundingClientRect(), config);
  });

  updateBackgroundLens();
}

function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();
  const deltaMs = clock.getDelta() * 1000;

  particles.rotation.y = t * 0.012;
  gifPlayers.forEach((player) => tickGifTexture(player, deltaMs));

  portalGroups.forEach(({ portal, glow, config }) => {
    const hover = hoveredPortal?.userData.id === config.id ? 1 : 0;
    if (portal.material.uniforms?.uHover) {
      portal.material.uniforms.uHover.value = THREE.MathUtils.lerp(
        portal.material.uniforms.uHover.value,
        hover,
        0.12,
      );
    }
    const baseGlow = 0.08;
    glow.material.opacity = THREE.MathUtils.lerp(glow.material.opacity, baseGlow + hover * 0.08, 0.12);
  });

  alignPortalsToSlots();
  renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  alignPortalsToSlots();
});

document.querySelectorAll('[data-portal]').forEach((gate) => {
  gate.addEventListener('mouseenter', () => {
    const mesh = portalMeshes.find((m) => m.userData.id === gate.dataset.portal);
    if (mesh) setHoveredPortal(mesh);
  });
  gate.addEventListener('mouseleave', () => setHoveredPortal(null));
});

alignPortalsToSlots();
animate();
