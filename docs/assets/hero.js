/* The order book as a landscape, built from a real spoof in the simulation
   (docs/data/terrain.js, written by build_site.py).
     x  = price (bids on the left, asks on the right; the valley between them is the spread)
     z  = time, running away from the viewer
     y  = lots waiting at that price
   The fake wall is coloured magenta. The camera flies forward through time.
   A "Pause motion" button stops the flight; reduced-motion users get a still frame. */
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.min.js";

const T = window.TERRAIN;
const canvas = document.querySelector("[data-terrain]");
const hero = document.querySelector(".hero");
const toggle = document.querySelector("[data-terrain-toggle]");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function webglOK() {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); }
  catch (e) { return false; }
}

if (T && canvas && hero && webglOK()) start();
else if (hero) hero.classList.add("no-terrain");

function start() {
  const nT = T.t.length;
  const nP = T.prices.length;
  const col = (row) => row.slice().reverse();                   // low price (bids) on the left
  const bid = T.bid.map(col), ask = T.ask.map(col), wall = T.wall.map(col);

  // --- Heights: gently smoothed over time so the book reads as land; the wall stays sharp ---
  const gauss = (sigma) => {
    const r = Math.ceil(sigma * 2.5), k = [];
    let s = 0;
    for (let i = -r; i <= r; i++) { const v = Math.exp(-(i * i) / (2 * sigma * sigma)); k.push(v); s += v; }
    return k.map((v) => v / s);
  };
  const smoothTime = (grid, sigma) => {
    const k = gauss(sigma), r = (k.length - 1) / 2;
    return grid.map((_, t) => grid[0].map((__, p) => {
      let s = 0;
      for (let j = -r; j <= r; j++) s += grid[Math.min(nT - 1, Math.max(0, t + j))][p] * k[j + r];
      return s;
    }));
  };
  const base = smoothTime(bid.map((row, t) => row.map((v, p) => v + ask[t][p] - wall[t][p])), 1.6);
  const fake = smoothTime(wall, 0.7);
  const bidShare = smoothTime(bid.map((row, t) => row.map((v, p) => (v + ask[t][p] > 0 ? v / (v + ask[t][p]) : 0.5))), 1.2);

  // Upsample across price so ridges are round rather than stepped.
  const UP = 4, nX = (nP - 1) * UP + 1;
  const sample = (grid, t, x) => {
    const f = x / UP, i = Math.floor(f), a = f - i;
    const v0 = grid[t][Math.min(i, nP - 1)], v1 = grid[t][Math.min(i + 1, nP - 1)];
    return v0 + (v1 - v0) * a * a * (3 - 2 * a);
  };

  const WIDTH = 30, STEP_Z = 0.42, HEIGHT = 0.085;
  const depthZ = (nT - 1) * STEP_Z;
  const geometry = new THREE.PlaneGeometry(WIDTH, depthZ, nX - 1, nT - 1);
  geometry.rotateX(-Math.PI / 2);
  const pos = geometry.attributes.position;
  const colours = new Float32Array(pos.count * 3);
  geometry.setAttribute("color", new THREE.BufferAttribute(colours, 3));
  const fakeAmt = new Float32Array(pos.count), sideAmt = new Float32Array(pos.count), heightAmt = new Float32Array(pos.count);
  let maxH = 0;
  for (let t = 0; t < nT; t++) {
    for (let x = 0; x < nX; x++) {
      const v = (nT - 1 - t) * nX + x;                         // row 0 is the latest step: time runs away from us
      const h = (sample(base, t, x) + sample(fake, t, x)) * HEIGHT;
      pos.setY(v, h);
      maxH = Math.max(maxH, h);
      fakeAmt[v] = Math.min(1, sample(fake, t, x) / 6);
      sideAmt[v] = sample(bidShare, t, x);
      heightAmt[v] = h;
    }
  }
  geometry.computeVertexNormals();

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xffffff, 10, 46);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
  scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0 })));

  // Thin ridgelines every few steps give the land a printed, measured texture.
  const linePts = [];
  for (let t = 0; t < nT; t += 6) {
    for (let x = 0; x < nX - 1; x++) {
      const a = (nT - 1 - t) * nX + x, b = a + 1;
      linePts.push(pos.getX(a), pos.getY(a) + 0.02, pos.getZ(a), pos.getX(b), pos.getY(b) + 0.02, pos.getZ(b));
    }
  }
  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(linePts, 3));
  const lines = new THREE.LineSegments(lineGeo, new THREE.LineBasicMaterial({ transparent: true, opacity: 0.16 }));
  scene.add(lines);
  const hemi = new THREE.HemisphereLight(0xffffff, 0x888888, 1.15);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xffffff, 1.35);
  sun.position.set(-8, 14, 10);
  scene.add(sun);

  const colour = (name) => new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888");
  function paint() {
    const low = colour("--terrain-low"), bidC = colour("--bid"), askC = colour("--ask"), mark = colour("--mark");
    const tmp = new THREE.Color();
    for (let v = 0; v < pos.count; v++) {
      tmp.copy(askC).lerp(bidC, sideAmt[v]);
      tmp.lerp(low, Math.max(0, 1 - heightAmt[v] / (maxH * 0.55)) * 0.75);
      tmp.lerp(mark, fakeAmt[v]);
      colours[v * 3] = tmp.r; colours[v * 3 + 1] = tmp.g; colours[v * 3 + 2] = tmp.b;
    }
    geometry.attributes.color.needsUpdate = true;
    scene.fog.color.copy(colour("--sky-horizon"));
    hemi.color.copy(colour("--sky-top"));
    hemi.groundColor.copy(low);
    lines.material.color.copy(colour("--ink"));
  }

  // Camera path: from well before the spoof to just after it, gliding forward in time.
  const zOf = (step) => depthZ / 2 - (step - T.t[0]) * STEP_Z;
  const fromZ = zOf(T.start - 75) + 14, toZ = zOf(T.end + 25) + 14;
  const DURATION = 22000, GAP = 1600;
  const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  function place(progress, sway) {
    const z = fromZ + (toZ - fromZ) * ease(progress);
    camera.position.set(2.2 + Math.sin(sway) * 0.7, 4.6 + Math.sin(sway * 0.7) * 0.2, z);
    camera.lookAt(2.6, 1.1, z - 24);
  }

  let progress = 0.78, sway = 0, paused = false, visible = true, raf = 0, last = 0, clock = 0;
  const still = () => { place(progress, sway); renderer.render(scene, camera); };
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = w < 700 ? 54 : 42;
    camera.updateProjectionMatrix();
    if (paused || reduceMotion.matches) still();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();
  paint();
  const repaint = () => { paint(); if (paused || reduceMotion.matches) still(); };
  window.addEventListener("themechange", repaint);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", repaint);

  function frame(now) {
    if (paused || !visible || document.hidden) { last = 0; return; }
    clock += last ? now - last : 0;
    last = now;
    const lapTime = clock % (DURATION + GAP), lap = Math.floor(clock / (DURATION + GAP));
    progress = Math.min(1, lapTime / DURATION);
    sway = clock / 4200;
    let opacity = 1;                                          // fade across the loop seam instead of jumping
    if (lapTime > DURATION) opacity = Math.max(0, 1 - (lapTime - DURATION) / 1000);
    else if (lap > 0 && lapTime < 1000) opacity = lapTime / 1000;
    canvas.style.opacity = opacity.toFixed(3);
    place(progress, sway);
    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  }
  const run = () => { cancelAnimationFrame(raf); if (!paused && visible && !document.hidden && !reduceMotion.matches) raf = requestAnimationFrame(frame); };

  function setPaused(value) {
    paused = value;
    if (toggle) {
      toggle.setAttribute("aria-pressed", String(paused));
      toggle.querySelector("span").textContent = paused ? "Resume motion" : "Pause motion";
      const icon = toggle.querySelector("i");
      if (icon) icon.className = `ph ${paused ? "ph-play" : "ph-pause"}`;
    }
    window.dispatchEvent(new CustomEvent("motionchange", { detail: { paused } }));
    if (paused) { canvas.style.opacity = "1"; still(); } else run();
  }

  hero.classList.add("terrain-ready");
  if (reduceMotion.matches) { still(); return; }
  if (toggle) { toggle.hidden = false; toggle.addEventListener("click", () => setPaused(!paused)); }
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; run(); }, { threshold: 0 }).observe(hero);
  document.addEventListener("visibilitychange", run);
  progress = 0;
  run();
}
