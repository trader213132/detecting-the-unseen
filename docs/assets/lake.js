/* A still lake, and a drop.
   The lake (lake-still.jpg) is perfectly still and clear. As the opening sequence finishes, a single
   drop of water falls into the sun's reflection, splashes, sends rings across the surface, and the
   water settles back to stillness. While the reader stays at the top, another drop follows after a
   few seconds of still water; it also falls when the reader returns to the top or taps the water.
   Decorative only: it carries no research data. */
(() => {
  const canvas = document.querySelector("[data-lake]"), scene = document.querySelector(".lake-scene");
  if (!canvas || !scene) return;
  const hero = document.querySelector(".hero"), toggle = document.querySelector("[data-lake-toggle]");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const IMG_ASPECT = 3840 / 2160, HORIZON = 262 / 2160;      // where the waterline sits in the image
  const FALL = 1.05, SETTLE = 6.2;                             // seconds: drop falling, water settling
  const STILL_GAP = 9;                                         // seconds of perfectly still water between drops
  const freeze = parseFloat(new URLSearchParams(location.search).get("lake-t"));   // for checking one frame

  // ---- scroll: fade the lake as the article begins ----
  let scrollQueued = false;
  function position() {
    scrollQueued = false;
    const distance = hero ? Math.min(1, Math.max(0, scrollY / (hero.offsetHeight * 0.8))) : 1;
    scene.style.opacity = String(1 - distance * 0.91);
    document.body.classList.toggle("lake-at-top", !!hero && scrollY < 48);
    document.documentElement.style.setProperty("--reading-progress",
      String(scrollY / Math.max(1, document.documentElement.scrollHeight - innerHeight)));
  }
  position();
  addEventListener("scroll", () => { if (!scrollQueued) { scrollQueued = true; requestAnimationFrame(position); } }, { passive: true });

  // ---- cover mapping, so the image fills any screen with the waterline kept in view ----
  // image uv = centre + (screen - .5) * extent. Narrow screens slide right, towards the sun's reflection.
  let centre = [0.5, 0.5], extent = [1, 1];
  function fit(w, h) {
    const screen = w / h;
    if (screen > IMG_ASPECT) {                                       // wide: crop top and bottom
      const ey = IMG_ASPECT / screen;
      extent = [1, ey];
      centre = [0.5, Math.min(1 - ey / 2, Math.max(ey / 2, 0.03 + ey / 2))];
    } else {                                                         // tall: crop the sides
      const ex = screen / IMG_ASPECT;
      extent = [ex, 1];
      const want = ex >= 0.75 ? 0.5 : 0.5 + (0.75 - ex) * 0.4;
      centre = [Math.min(1 - ex / 2, Math.max(ex / 2, want)), 0.5];
    }
    // the still image shown before WebGL starts (or instead of it) uses the same crop
    const bx = extent[0] < 1 ? (centre[0] - extent[0] / 2) / (1 - extent[0]) : 0.5;
    const by = extent[1] < 1 ? (centre[1] - extent[1] / 2) / (1 - extent[1]) : 0.5;
    scene.style.backgroundPosition = `${(bx * 100).toFixed(2)}% ${(by * 100).toFixed(2)}%`;
  }
  fit(innerWidth, innerHeight);

  let gl;
  try { gl = canvas.getContext("webgl", { alpha: false, antialias: false, depth: false, powerPreference: "low-power" }); } catch (_) {}
  if (!gl) { scene.dataset.render = "static"; return; }

  const vertex = "attribute vec2 a;varying vec2 v;void main(){v=a*.5+.5;gl_Position=vec4(a,0.,1.);}";
  const fragment = `precision highp float;
varying vec2 v;
uniform sampler2D lake;
uniform vec2 res, centre, extent;      // cover mapping: image uv = centre + (screen - .5) * extent
uniform vec2 P;                        // impact point, image uv
uniform float t, squash, horizon, aspect, y0;   // y0: where the drop enters, just above the screen
const float FALL = ${FALL.toFixed(2)};
const float RD = 0.0165;               // drop radius, in image heights

vec3 img(vec2 uv){ return texture2D(lake, clamp(uv, vec2(.0005), vec2(.9995))).rgb; }

// Height of the water at world offset q (image heights), for rings started 'age' seconds ago.
float rings(vec2 q, float age, float amp){
  if (age <= 0.0) return 0.0;
  float r = length(q), h = 0.0;
  for (int j = 0; j < 4; j++) {
    float R = 0.115 * (age - float(j) * 0.11);
    if (R <= 0.0) continue;
    float w = 0.010 + 0.012 * age;
    float band = (r - R) / w;
    h += exp(-band * band) * sin(band * 2.6) * (1.0 - float(j) * 0.2);
  }
  return h * amp * exp(-age / 1.35) / (1.0 + 9.0 * r);
}
float height(vec2 q, float a){ return rings(q, a, 1.0) + rings(q, a - 0.62, 0.35); }

// A drop of water is a tiny ball lens: it shows the whole scene upside down and squeezed (bright
// sky at its bottom, dark water at its top), reflects the sky at its rim, and has a dark edge.
vec4 drop(vec2 uv, vec2 c, float rad, float stretch, float strength){
  vec2 d = vec2((uv.x - c.x) * aspect, (uv.y - c.y) / stretch) / rad;
  float l = length(d);
  if (l > 1.04) return vec4(0.0);
  float z = sqrt(max(0.0, 1.0 - l * l));
  vec2 look = -d * (0.04 + 0.46 * l * l);                          // inverted, wide-angle view
  vec3 refr = img(vec2(c.x + look.x / aspect, max(horizon * 0.4, c.y + look.y))) * 1.06 + 0.012;
  float fres = 0.03 + 0.97 * pow(1.0 - z, 5.0);
  vec3 sky = img(vec2(c.x - d.x * 0.06, horizon * 0.4));
  vec3 col = mix(refr, sky * 1.25, fres * 0.85);
  col *= mix(1.0, 0.22, smoothstep(0.82, 0.985, l));               // the dark outline of a real drop
  col += vec3(1.0, 0.95, 0.86) * 0.30 * exp(-pow((d.y - 0.60) / 0.17, 2.0)) * exp(-d.x * d.x / 0.16);  // caustic
  vec2 s1 = d - vec2(-0.30, -0.46), s2 = d - vec2(0.36, 0.30);
  col += vec3(1.0, 0.98, 0.94) * (exp(-dot(s1, s1) / 0.010) * 1.25 + exp(-dot(s2, s2) / 0.004) * 0.25);
  return vec4(col, (1.0 - smoothstep(0.96, 1.04, l)) * strength);
}

void main(){
  vec2 p = vec2(v.x, 1.0 - v.y);
  vec2 uv = centre + (p - 0.5) * extent;
  float a = t - FALL;                                             // seconds since impact

  // --- the water: still, unless rings are passing ---
  vec2 off = uv - P;
  vec2 q = vec2(off.x * aspect, off.y * squash);
  vec3 col;
  if (a > 0.0 && uv.y > horizon) {
    float e = 0.0015;
    float hx = height(q + vec2(e, 0.0), a) - height(q - vec2(e, 0.0), a);
    float hz = height(q + vec2(0.0, e), a) - height(q - vec2(0.0, e), a);
    vec2 slope = vec2(hx, hz) / (2.0 * e);
    // A tilted facet reflects a very different patch of sky (the angle doubles on reflection), so
    // even gentle rings show as bright and dark bands; facets turned away from us reflect more.
    vec2 bend = vec2(clamp(slope.x * 0.0016, -0.08, 0.08), clamp(slope.y * 0.0065, -0.42, 0.42));
    vec2 su = uv + bend;
    su.y = max(su.y, horizon + 0.004);                             // still a reflection: never the sky itself
    col = img(su) * (1.0 + clamp(-slope.y * 0.0035, -0.35, 0.45));
    col += vec3(0.95, 0.93, 0.88) * pow(clamp(-slope.y * 0.012, 0.0, 1.0), 3.0) * 0.18;   // crests catching the light
    float flash = exp(-dot(q, q) / 0.00012) * exp(-a * 14.0);      // the moment of contact
    col = mix(col, col * 0.55, flash * 0.6);
  } else {
    col = img(uv);
  }

  // --- the drop, its reflection, and the splash ---
  if (t < FALL) {
    float k = t / FALL;
    float y = mix(y0, P.y, k * k);
    float stretch = 1.0 + 0.45 * k * k;                            // motion blur as it speeds up
    vec2 c = vec2(P.x, y);
    vec2 tail = vec2((uv.x - c.x) * aspect / RD, (uv.y - c.y) / RD);
    if (tail.y < 0.0 && tail.y > -9.0 * k) col += vec3(0.85, 0.9, 0.95) * 0.06 * k * exp(-tail.x * tail.x * 3.0) * (1.0 + tail.y / (9.0 * k));
    vec4 dr = drop(uv, c, RD, stretch, 1.0);
    vec2 mirror = vec2(c.x, P.y + (P.y - c.y));
    vec4 rf = drop(uv, mirror, RD, stretch, 0.55 * smoothstep(0.35, 0.95, k));
    col = mix(col, rf.rgb * 0.75, rf.a);
    col = mix(col, dr.rgb, dr.a);
  } else if (a < 1.2) {
    // crown: a ring of small droplets thrown up and out
    for (int i = 0; i < 9; i++) {
      float th = float(i) * 0.6981 + 0.3 * sin(float(i) * 7.1);
      float sp = 0.05 + 0.02 * fract(sin(float(i) * 13.7) * 43.1);
      float up = 0.30 + 0.12 * fract(sin(float(i) * 3.3) * 91.7);
      float hgt = up * a - 1.6 * a * a;
      if (hgt <= 0.0) continue;
      vec2 c = P + vec2(cos(th) * sp * a / aspect, sin(th) * sp * a / squash - hgt * 0.35);
      vec4 dr = drop(uv, c, RD * 0.32, 1.0, 1.0);
      col = mix(col, dr.rgb, dr.a);
    }
    // the jet that springs back up, and the drop it throws off
    float ja = a - 0.10;
    if (ja > 0.0 && ja < 0.36) {
      float hj = 0.034 * sin(3.14159 * ja / 0.36);
      vec2 j = vec2((uv.x - P.x) * aspect, P.y - uv.y);
      float wj = RD * (0.55 - 0.25 * j.y / max(hj, 1e-4));
      if (j.y > 0.0 && j.y < hj && abs(j.x) < wj) {
        float edge = abs(j.x) / wj;
        vec3 jc = img(vec2(P.x - j.x / aspect * 4.0, P.y - j.y * 0.6)) * 0.95;
        jc *= mix(1.0, 0.45, smoothstep(0.6, 1.0, edge));
        jc += vec3(0.25) * exp(-pow((j.x / wj - 0.35) / 0.18, 2.0));
        col = mix(col, jc, 1.0 - smoothstep(0.85, 1.0, edge));
      }
    }
    float pa = a - 0.28;
    if (pa > 0.0) {
      float hp = 0.034 + 0.12 * pa - 0.62 * pa * pa;
      if (hp > 0.0) { vec4 dr = drop(uv, vec2(P.x, P.y - hp), RD * 0.45, 1.0, 1.0); col = mix(col, dr.rgb, dr.a); }
    }
  }
  gl_FragColor = vec4(col, 1.0);
}`;

  function shader(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s));
    return s;
  }
  let program;
  try {
    program = gl.createProgram();
    gl.attachShader(program, shader(gl.VERTEX_SHADER, vertex));
    gl.attachShader(program, shader(gl.FRAGMENT_SHADER, fragment));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error("lake shader link failed");
  } catch (e) { console.warn("Static lake fallback:", e.message); scene.dataset.render = "static"; return; }
  gl.useProgram(program);
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
  const aLoc = gl.getAttribLocation(program, "a");
  gl.enableVertexAttribArray(aLoc);
  gl.vertexAttribPointer(aLoc, 2, gl.FLOAT, false, 0, 0);
  const U = (n) => gl.getUniformLocation(program, n);
  const u = { res: U("res"), centre: U("centre"), extent: U("extent"), P: U("P"), t: U("t"), squash: U("squash"),
    horizon: U("horizon"), aspect: U("aspect"), y0: U("y0") };
  gl.uniform1f(u.horizon, HORIZON);
  gl.uniform1f(u.aspect, IMG_ASPECT);

  function cover() {
    fit(canvas.width, canvas.height);
    gl.uniform2f(u.centre, centre[0], centre[1]);
    gl.uniform2f(u.extent, extent[0], extent[1]);
    gl.uniform1f(u.y0, centre[1] - extent[1] / 2 - 0.04);
  }

  // The camera looks across the water from just above it: rings far away look flatter.
  function setImpact(x, y) {
    const f = 0.5 / Math.tan((11 * Math.PI) / 180);
    const pitch = Math.atan((0.5 - HORIZON) / f);
    const angle = Math.atan((y - 0.5) / f) + pitch;
    gl.uniform2f(u.P, x, y);
    gl.uniform1f(u.squash, 1 / Math.max(0.08, Math.sin(angle)));
  }
  // Where the drop lands by default: in the sun's reflection, clear of the words.
  function landing() {
    const portrait = innerWidth / innerHeight < 0.9;
    const sx = portrait ? 0.76 : 0.8, sy = portrait ? 0.86 : 0.64;
    return [centre[0] + (sx - 0.5) * extent[0], Math.max(HORIZON + 0.12, centre[1] + (sy - 0.5) * extent[1])];
  }

  let ready = false, lost = false, paused = false, raf = 0, startedAt = -1;
  const texture = gl.createTexture();
  function draw(time) {
    if (!ready || lost) return;
    gl.uniform2f(u.res, canvas.width, canvas.height);
    gl.uniform1f(u.t, time);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }
  const STILL = 1e4;                                                  // a time long after everything has settled
  function frame(now) {
    if (startedAt < 0 || paused || lost) return;
    const tt = (now - startedAt) / 1000;
    if (tt > FALL + SETTLE) {                                       // still again: stop drawing frames
      startedAt = -1; draw(STILL);
      clearTimeout(nextDrop);
      nextDrop = setTimeout(() => fallOnce(), STILL_GAP * 1000);     // another drop, while the reader is still here
      return;
    }
    draw(tt);
    raf = requestAnimationFrame(frame);
  }
  let nextDrop = 0;
  function fallOnce(x, y) {
    clearTimeout(nextDrop);
    if (!ready || lost || paused || reduced.matches || document.hidden) return;
    if (hero && hero.getBoundingClientRect().bottom < innerHeight * 0.5) return;   // nobody is looking at the water
    if (x !== undefined) setImpact(x, y); else setImpact(...landing());
    cancelAnimationFrame(raf);
    startedAt = performance.now();
    raf = requestAnimationFrame(frame);
  }
  function resize() {
    const ratio = Math.min(devicePixelRatio || 1, 2, Math.sqrt(3200000 / (innerWidth * innerHeight)));
    canvas.width = Math.round(innerWidth * ratio);
    canvas.height = Math.round(innerHeight * ratio);
    gl.viewport(0, 0, canvas.width, canvas.height);
    cover();
    position();
    if (startedAt < 0) draw(Number.isFinite(freeze) ? freeze : STILL);
  }

  function preference() {
    const stopped = paused || reduced.matches;
    document.documentElement.dataset.motion = stopped ? "paused" : "running";
    document.body.classList.toggle("motion-paused", stopped);
    if (toggle) {
      toggle.hidden = reduced.matches || !ready || lost || !hero;
      toggle.textContent = paused ? "Resume motion" : "Pause motion";
      toggle.setAttribute("aria-pressed", String(paused));
    }
    dispatchEvent(new CustomEvent("motionchange", { detail: { paused: stopped } }));
    if (stopped) { cancelAnimationFrame(raf); startedAt = -1; draw(STILL); }
  }

  // The first drop lands just after the headline has finished rising (masthead.js marks the start).
  function firstDrop() {
    if (!hero) return;
    const root = document.documentElement;
    const after = (at) => setTimeout(() => fallOnce(), Math.max(150, at + 1250 - performance.now()));
    if (root.dataset.introAt) after(+root.dataset.introAt);
    else if (root.classList.contains("intro")) addEventListener("intro:play", () => after(+root.dataset.introAt), { once: true });
    else after(performance.now() - 650);
  }

  const image = new Image();
  image.onload = () => {
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, image);
    ready = true;
    scene.dataset.render = "live";
    setImpact(...landing());
    resize();
    preference();
    if (!Number.isFinite(freeze)) firstDrop();
  };
  image.onerror = () => { scene.dataset.render = "static"; };
  image.src = new URL("lake-still.jpg", import.meta.url).href;

  // Another drop only when the reader comes back to the top of the page...
  if (hero) {
    let left = false;
    new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) left = true;
      else if (left) { left = false; setTimeout(() => fallOnce(), 500); }
    }, { threshold: 0.6 }).observe(hero);
    // ...or taps the water itself.
    hero.addEventListener("click", (e) => {
      if (e.target.closest("a, button, input, select, textarea, [role='tab']")) return;
      const x = centre[0] + (e.clientX / innerWidth - 0.5) * extent[0];
      const y = centre[1] + (e.clientY / innerHeight - 0.5) * extent[1];
      if (y > HORIZON + 0.06) fallOnce(x, y);
    });
  }
  toggle?.addEventListener("click", () => { paused = !paused; preference(); });
  addEventListener("resize", resize, { passive: true });
  document.addEventListener("visibilitychange", () => { if (document.hidden) { cancelAnimationFrame(raf); startedAt = -1; draw(STILL); } });
  reduced.addEventListener("change", preference);
  canvas.addEventListener("webglcontextlost", (e) => {
    e.preventDefault(); lost = true; cancelAnimationFrame(raf); scene.dataset.render = "static"; if (toggle) toggle.hidden = true;
  });
})();
