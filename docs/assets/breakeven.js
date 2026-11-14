/* Break-Even Lab: when does a spoof pay?
   Data: window.BREAKEVEN (docs/data/breakeven.js, written by run_breakeven.py).
   Sections follow the four animation prompts: the wall, the equation, the map, the seal. */
(() => {
  "use strict";
  const D = window.BREAKEVEN;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const NS = "http://www.w3.org/2000/svg";
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  const seg = (P, a, b) => clamp((P - a) / (b - a), 0, 1);
  const easeOutExpo = t => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));
  const easeInOutCubic = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const easeOutCubic = t => 1 - Math.pow(1 - t, 3);
  const easeInOutSine = t => -(Math.cos(Math.PI * t) - 1) / 2;
  const fmt = (x, d = 2) => (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toFixed(d);
  const pct = x => Math.round(x * 100) + "%";
  const svg = (tag, attrs = {}, parent) => {
    const el = document.createElementNS(NS, tag);
    for (const k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
  };
  const inView = (el, cb, threshold = 0.3) => {
    if (!el) return;
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.disconnect(); cb(); } }), { threshold });
    io.observe(el);
  };
  const mulberry = seed => () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const cellOf = (arrival, react, regime, size) => D.cells.find(c => c.arrival === arrival && c.react === react && c.regime === regime && c.size === size);
  const pays = c => c.net_lo > 0;

  /* =====================================================================
     1 · THE WALL
     ===================================================================== */
  function hero() {
    const sec = $("[data-hero]"), cv = $("[data-book]"), ctx = cv.getContext("2d");
    const h1 = $("[data-split]"), steps = $$("[data-steps] li");
    // split the headline into words and characters
    let n = 0;
    const split = node => {
      [...node.childNodes].forEach(ch => {
        if (ch.nodeType === 3) {
          const frag = document.createDocumentFragment();
          ch.textContent.split(/(\s+)/).forEach(part => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(" ")); return; }
            const w = document.createElement("span"); w.className = "w";
            [...part].forEach(c => { const s = document.createElement("span"); s.className = "ch"; s.textContent = c; s.style.transitionDelay = (150 + n++ * 18) + "ms"; w.appendChild(s); });
            frag.appendChild(w);
          });
          ch.replaceWith(frag);
        } else split(ch);
      });
    };
    h1.setAttribute("aria-label", h1.textContent); split(h1);
    requestAnimationFrame(() => requestAnimationFrame(() => h1.classList.add("is-in")));
    $$(".be-hero__eqline span").forEach((s, i) => (s.style.transitionDelay = i * 60 + "ms"));

    let W = 0, H = 0, dpr = 1;
    const resize = () => {
      dpr = Math.min(2, devicePixelRatio || 1);
      const r = cv.getBoundingClientRect(); W = r.width; H = r.height;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const noise = (x, t) => 0.5 * Math.sin(x * 1.7 + t * 1.57) + 0.3 * Math.sin(x * 3.1 - t * 2.3 + 1.3) + 0.2 * Math.sin(x * 5.3 + t * 0.9 + 4.1);
    const ROWS = 20, dots = [];
    let lastSpawn = 0, Ps = reduced ? 0.45 : 0, Pt = 0;
    const rnd = mulberry(7);
    const burst = Array.from({ length: 60 }, () => ({ u: rnd(), a: rnd() * Math.PI * 2, v: 20 + rnd() * 40, s: 1.5 + rnd() * 1.5 }));

    function frame(now) {
      const t = now / 1000, P = Ps;
      ctx.clearRect(0, 0, W, H);
      const rowH = W < 520 ? 18 : Math.min(26, (H - 120) / ROWS);
      const top = (H - rowH * ROWS) / 2;
      const cx = W < 520 ? W / 2 : W * 0.5, colW = 64;
      const half = Math.min(W / 2 - colW / 2 - 12, 420);
      const unit = half / (3.4 * 12.5);
      const kLean = easeInOutCubic(seg(P, 0.35, 0.55)) * (1 - easeInOutCubic(seg(P, 0.6, 0.75)));
      const shift = easeInOutCubic(seg(P, 0.35, 0.55)) * (1 - 0.5 * seg(P, 0.75, 1));
      const midY = top + (10 + shift) * rowH;
      let largest = 0, bestBidY = null;
      // rows
      ctx.font = "11px 'JetBrains Mono', monospace"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      for (let i = 0; i < ROWS; i++) {
        const yc = top + (i + 0.5) * rowH, dist = Math.abs(yc - midY) / rowH, ask = yc < midY;
        let depth = (3 + 9 * Math.exp(-dist / 4)) * (1 + 0.12 * noise(i, t));
        largest = Math.max(largest, depth);
        if (ask && dist < 4) depth *= 1 + 0.25 * kLean;
        if (!ask) depth *= 1 - 0.18 * kLean;
        const fade = clamp(dist * 2 - 0.2, 0, 1);
        const w = depth * unit * fade;
        if (!ask && bestBidY === null) bestBidY = yc;
        ctx.fillStyle = ask ? "#5d6678" : "#a3abbb";
        const x = ask ? cx + colW / 2 : cx - colW / 2 - w;
        roundRect(x, yc - rowH * 0.32, w, rowH * 0.64, 3);
        ctx.fillStyle = "rgba(248,250,252,0.06)"; ctx.fillRect(cx - half - colW / 2, top + i * rowH, 2 * half + colW, 1);
        ctx.fillStyle = "rgba(248,250,252,0.45)"; ctx.fillText(String(1010 - i), cx, yc);
      }
      // the wall (fixed price: 2 rows above the original best ask)
      const wallY = top + 7.5 * rowH, wallK = easeOutExpo(seg(P, 0.15, 0.35)) * (P < 0.55 ? 1 : 0);
      const wallW = wallK * 3.2 * largest * unit;
      if (wallW > 0.5) {
        ctx.save(); ctx.shadowBlur = 24; ctx.shadowColor = "rgba(238,95,149,0.55)"; ctx.fillStyle = "#ee5f95";
        roundRect(cx + colW / 2, wallY - rowH * 0.36, wallW, rowH * 0.72, 3); ctx.restore();
        if (wallK > 0.6) {
          ctx.fillStyle = `rgba(255,136,179,${(wallK - 0.6) / 0.4})`; ctx.textAlign = "right";
          ctx.fillText("SPOOF WALL · 16×", cx + colW / 2 + wallW - 8, wallY - rowH * 0.36 - 9); ctx.textAlign = "center";
        }
      }
      const kb = seg(P, 0.55, 0.7);
      if (kb > 0 && kb < 1) {
        const full = 3.2 * largest * unit;
        burst.forEach(b => {
          const ox = cx + colW / 2 + b.u * full, d = easeOutCubic(kb) * b.v * 1.6;
          ctx.fillStyle = `rgba(238,95,149,${1 - kb})`;
          ctx.fillRect(ox + Math.cos(b.a) * d, wallY + Math.sin(b.a) * d, b.s, b.s);
        });
      }
      // genuine order pill at the best bid
      const kp = seg(P, 0.38, 0.55), fadeOut = 1 - seg(P, 0.66, 0.74);
      if (kp > 0 && fadeOut > 0 && bestBidY !== null) {
        const flash = kp < 0.5 ? (Math.floor(kp * 8) % 2 ? 0.35 : 1) : 1;
        const label = "GENUINE BUY · FILLS", pw = 150, ph = 20, px = cx - colW / 2 - pw - 10, py = bestBidY - ph / 2;
        ctx.globalAlpha = flash * fadeOut * Math.min(1, kp * 4);
        ctx.strokeStyle = "#f8fafc"; ctx.lineWidth = 1; ctx.fillStyle = "rgba(15,18,23,0.85)";
        roundRect(px, py, pw, ph, 10, true);
        ctx.fillStyle = "#f8fafc"; ctx.fillText(label, px + pw / 2, py + ph / 2 + 0.5);
        ctx.globalAlpha = 1;
      }
      // mid line
      ctx.setLineDash([4, 5]); ctx.strokeStyle = "rgba(248,250,252,0.4)"; ctx.beginPath();
      ctx.moveTo(cx - half - colW / 2, midY); ctx.lineTo(cx + half + colW / 2, midY); ctx.stroke(); ctx.setLineDash([]);
      // trader dots
      if (!reduced) {
        if (now - lastSpawn > 180) {
          lastSpawn = now;
          const sell = Math.random() < 0.5 + 0.35 * kLean, row = sell ? Math.floor(Math.random() * 6) + 4 : Math.floor(Math.random() * 6) + 10;
          dots.push({ x: sell ? cx + half + colW / 2 : cx - half - colW / 2, row, life: 0, side: sell ? 1 : -1 });
        }
        for (let i = dots.length - 1; i >= 0; i--) {
          const d = dots[i], yc = top + (d.row + 0.5) * rowH, tx = cx + d.side * (colW / 2 + 30);
          d.x = lerp(d.x, tx, 0.06); d.life++;
          const near = Math.abs(d.x - tx) < 8, r = near ? 2.5 * clamp(1 - (d.life - d.arr) / 6, 0, 1) : 2.5;
          if (near && d.arr === undefined) d.arr = d.life;
          if (r <= 0) { dots.splice(i, 1); continue; }
          ctx.fillStyle = "rgba(248,250,252,0.6)"; ctx.beginPath(); ctx.arc(d.x, yc, r, 0, 7); ctx.fill();
        }
      }
      // captions and the equation swap
      const k = P < 0.15 ? 0 : P < 0.35 ? 1 : P < 0.55 ? 2 : 3;
      steps.forEach((s, i) => s.classList.toggle("is-on", i === k && P < 0.72));
      sec.classList.toggle("is-eq", P >= 0.7 && !reduced);
      cv.style.opacity = P >= 0.7 ? (innerWidth < 900 ? 0.2 : 0.35) : "";
    }
    function roundRect(x, y, w, h, r, stroke) {
      r = Math.min(r, w / 2, h / 2); if (w <= 0) return;
      ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); ctx.fill(); if (stroke) ctx.stroke();
    }
    const target = () => {
      const r = sec.getBoundingClientRect();
      Pt = clamp(-r.top / (sec.offsetHeight - innerHeight), 0, 1);
    };
    resize(); addEventListener("resize", () => { resize(); if (reduced) frame(performance.now()); });
    if (reduced) { frame(performance.now()); return; }
    let visible = true, raf = 0;
    const loop = now => { Ps += (Pt - Ps) * 0.12; frame(now); raf = visible ? requestAnimationFrame(loop) : 0; };
    new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible && !raf) raf = requestAnimationFrame(loop); }).observe(sec);
    addEventListener("scroll", target, { passive: true }); target();
    raf = requestAnimationFrame(loop);
  }

  /* =====================================================================
     2 · THE EQUATION (shared state for sections 2, 5 and 6)
     ===================================================================== */
  const state = { G: 0.34, U: 0.03, C: 0, p: 0.85, F: 0.2 };
  const subs = [];
  const emit = () => subs.forEach(f => f(state));
  const net = s => s.G - s.U - s.C - s.p * s.F;

  function spring(v = 0) { return { v, x: v, t: v, vel: 0 }; }
  function stepSpring(s, dt) {
    if (reduced) { s.x = s.t; s.vel = 0; return false; }
    const a = 170 * (s.t - s.x) - 22 * s.vel; s.vel += a * dt; s.x += s.vel * dt;
    if (Math.abs(s.t - s.x) < 1e-4 && Math.abs(s.vel) < 1e-4) { s.x = s.t; s.vel = 0; return false; }
    return true;
  }

  function equation() {
    const sliders = $$("[data-sliders] input"), outs = {};
    $$("[data-o]").forEach(o => (outs[o.dataset.o] = o));
    const units = { G: " lots", U: " lots", C: " lots", p: "", F: " lots" };
    const paint = inp => {
      const k = inp.dataset.k, v = +inp.value;
      inp.style.setProperty("--fill", ((v - inp.min) / (inp.max - inp.min)) * 100 + "%");
      outs[k].textContent = k === "p" ? pct(v) : v.toFixed(2);
      inp.setAttribute("aria-valuetext", k === "p" ? pct(v) : v.toFixed(2) + units[k]);
    };
    const sync = () => sliders.forEach(inp => { inp.value = state[inp.dataset.k]; paint(inp); });
    sliders.forEach(inp => inp.addEventListener("input", () => {
      state[inp.dataset.k] = +inp.value; paint(inp); $$("[data-preset]").forEach(b => b.classList.remove("is-on")); emit();
    }));
    subs.push(sync);

    // presets: tween the measured values in over 450 ms
    $$("[data-preset]").forEach(btn => btn.addEventListener("click", () => {
      const [a, r, reg, sz] = btn.dataset.preset.split("|");
      const c = cellOf(+a, +r, reg, +sz); if (!c) return;
      $$("[data-preset]").forEach(b => b.classList.toggle("is-on", b === btn));
      const from = { ...state }, to = { G: +c.G.toFixed(2), U: +c.U.toFixed(2), C: 0, p: +c.p_life.toFixed(2) }, t0 = performance.now();
      const tick = now => {
        const k = reduced ? 1 : easeInOutCubic(clamp((now - t0) / 450, 0, 1));
        for (const key in to) state[key] = lerp(from[key], to[key], k);
        emit(); if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }));

    // odometer
    const odo = $("[data-odo]"), cap = $("[data-verdict]"), fs = $("[data-fstar]");
    odo.innerHTML = "";
    const sign = document.createElement("span"); sign.className = "be-odo__s"; odo.appendChild(sign);
    const strips = [];
    const addDigit = () => {
      const d = document.createElement("span"); d.className = "be-odo__d";
      const s = document.createElement("span"); s.className = "be-odo__strip";
      for (let i = 0; i <= 9; i++) { const x = document.createElement("span"); x.textContent = i; s.appendChild(x); }
      d.appendChild(s); odo.appendChild(d); strips.push(s);
    };
    addDigit(); const dot = document.createElement("span"); dot.textContent = "."; odo.appendChild(dot); addDigit(); addDigit();
    const u = document.createElement("span"); u.className = "be-odo__u"; u.textContent = "lots / attempt"; odo.appendChild(u);
    strips.forEach((s, i) => (s.style.transitionDelay = i * 30 + "ms"));
    const renderOdo = () => {
      const v = net(state), a = Math.min(9.99, Math.abs(v)), txt = a.toFixed(2).replace(".", "");
      sign.textContent = v > 0.004 ? "+" : v < -0.004 ? "−" : "";
      [...txt].forEach((ch, i) => (strips[i].style.transform = `translateY(${-ch}em)`));
      odo.classList.toggle("is-pos", v > 0.004);
      odo.setAttribute("aria-label", `Net payoff ${fmt(v)} lots per attempt`);
      cap.classList.toggle("is-pos", v > 0.004);
      cap.innerHTML = v > 0.004 ? "<strong>Pays:</strong> a positive expected profit per attempt" : "<strong>Does not pay:</strong> the expected payoff is zero or negative";
      const A = state.G - state.U - state.C;
      fs.innerHTML = A <= 0 ? "Break-even sanction: <strong>none needed</strong>. It doesn’t pay even with no penalty."
        : state.p <= 0 ? "With no chance of being caught, no sanction can deter it."
        : `Break-even sanction <strong>F* = (G − U − C) / p = ${(A / state.p).toFixed(2)}</strong> lots per attempt`;
    };

    // waterfall
    const fall = $("[data-fall]"), X0 = 40, CW = 72, GAP = 40, TOP = 34, BOT = 320;
    const cols = ["G", "−U", "−C", "−pF", "NET"];
    const els = cols.map((name, i) => {
      const x = X0 + i * (CW + GAP);
      return { x, r: svg("rect", { x, width: CW, rx: 4, class: i === 0 ? "r-g" : i === 4 ? "r-n" : "r-c" }, fall),
        val: svg("text", { x: x + CW / 2, "text-anchor": "middle" }, fall),
        lab: svg("text", { x: x + CW / 2, y: 352, "text-anchor": "middle", class: "lab" }, fall), a: spring(0), b: spring(0) };
    });
    els.forEach((e, i) => (e.lab.textContent = cols[i]));
    const conns = [0, 1, 2, 3].map(() => svg("line", { class: "conn" }, fall));
    const zero = svg("line", { x1: X0 - 16, x2: X0 + 5 * CW + 4 * GAP + 16, class: "zero" }, fall);
    const zl = svg("text", { x: X0 - 20, "text-anchor": "end" }, fall); zl.textContent = "0";
    const dom = { lo: spring(-0.5), hi: spring(1) };
    let shown = reduced;
    const targets = () => {
      const s = state, g = s.G, a1 = g - s.U, a2 = a1 - s.C, n = net(s);
      return [[0, g], [g, a1], [a1, a2], [a2, n], [0, n]];
    };
    const setTargets = () => {
      const tg = targets();
      els.forEach((e, i) => { if (shown || e.started) { e.a.t = tg[i][0]; e.b.t = tg[i][1]; } });
      const all = tg.flat();
      dom.lo.t = Math.min(-0.25, Math.min(...all) - 0.1); dom.hi.t = Math.max(0.6, Math.max(...all) + 0.15);
    };
    let anim = 0;
    const draw = () => {
      let moving = false;
      [dom.lo, dom.hi, ...els.flatMap(e => [e.a, e.b])].forEach(s => (moving = stepSpring(s, 1 / 60) || moving));
      const y = v => BOT - ((v - dom.lo.x) / (dom.hi.x - dom.lo.x)) * (BOT - TOP);
      els.forEach((e, i) => {
        const y1 = y(e.a.x), y2 = y(e.b.x), lo = Math.min(y1, y2), h = Math.max(0.5, Math.abs(y2 - y1));
        e.r.setAttribute("y", lo); e.r.setAttribute("height", h);
        const v = i === 0 ? e.b.x : i === 4 ? e.b.x : e.b.x - e.a.x;
        e.val.textContent = fmt(v); e.val.setAttribute("y", Math.min(y1, y2) - 8);
        if (i === 4) e.r.classList.toggle("is-pos", e.b.x > 0.004);
      });
      conns.forEach((c, i) => { const yy = y(els[i].b.x); c.setAttribute("x1", els[i].x + CW); c.setAttribute("x2", els[i + 1].x); c.setAttribute("y1", yy); c.setAttribute("y2", yy); });
      zero.setAttribute("y1", y(0)); zero.setAttribute("y2", y(0)); zl.setAttribute("y", y(0) + 4);
      anim = moving ? requestAnimationFrame(draw) : 0;
    };
    const kick = () => { setTargets(); if (!anim) anim = requestAnimationFrame(draw); };
    subs.push(renderOdo, kick);
    inView(fall, () => {
      els.forEach((e, i) => setTimeout(() => { e.started = true; kick(); if (i === 4) shown = true; }, reduced ? 0 : i * 120));
    }, 0.35);
  }

  /* =====================================================================
     3 · THE MAP
     ===================================================================== */
  function map() {
    const ARR = [2.25, 1.5, 1.0], RE = [0, 3, 6, 9];
    const opt = { size: 16, regime: "both", det: "life", F: 0 };
    const panels = $("[data-panels]"), cap = $("[data-mapcap]"), tip = $("[data-tip]");
    const fIn = $("[data-mapf]"), fOut = $("[data-mapfo]");

    // stat tiles, computed from the data
    const paying = D.cells.filter(pays), nofeed = D.cells.filter(c => c.react === 0);
    const fmax = Math.max(...paying.map(c => c.Fstar_life));
    const stats = { pays: [paying.length, ` / ${D.cells.length}`, 0], nofeed: [nofeed.filter(pays).length, ` / ${nofeed.length}`, 0], fmax: [fmax, "", 2] };
    const statEls = $$("[data-stat]");
    statEls.forEach(el => { const [v, tail, d] = stats[el.dataset.stat]; el.textContent = v.toFixed(d) + tail; });
    inView($("[data-stats]"), () => {
      if (reduced) return;
      const t0 = performance.now();
      const tick = now => {
        const k = easeOutCubic(clamp((now - t0) / 1100, 0, 1));
        statEls.forEach(el => { const [v, tail, d] = stats[el.dataset.stat]; el.textContent = (v * k).toFixed(d) + tail; });
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, 0.5);

    // segmented controls
    const segs = $$("[data-seg]");
    const placeInd = sg => {
      const on = $("[aria-checked='true']", sg), ind = $(".be-seg__ind", sg);
      ind.style.width = on.offsetWidth + "px"; ind.style.transform = `translateX(${on.offsetLeft}px)`;
    };
    segs.forEach(sg => {
      $$("button", sg).forEach(b => b.addEventListener("click", () => {
        $$("button", sg).forEach(x => x.setAttribute("aria-checked", x === b ? "true" : "false"));
        placeInd(sg);
        const k = sg.dataset.seg; opt[k] = k === "size" ? +b.dataset.v : b.dataset.v;
        build(k !== "det");
      }));
      $$("button", sg).forEach(b => b.getAttribute("aria-checked") || b.setAttribute("aria-checked", "false"));
    });
    const placeAll = () => segs.forEach(placeInd);
    addEventListener("resize", placeAll); document.fonts && document.fonts.ready.then(placeAll); placeAll();

    const S = 100, G6 = 6, L = 92, T = 8;
    let cellEls = [], waved = false;
    const value = c => c.net - (opt.det === "life" ? c.p_life : c.p_rule) * opt.F;
    const isPay = c => pays(c) && value(c) > 0;
    const paint = (e, c) => {
      const v = value(c), bg = $(".bg", e);
      if (v > 0) { bg.style.fill = "var(--mark)"; bg.style.fillOpacity = 0.25 + 0.75 * Math.min(v / 0.35, 1); }
      else { bg.style.fill = "var(--ink-3)"; bg.style.fillOpacity = 0.12 + 0.38 * Math.min(-v / 1.0, 1); }
      const light = v > 0 && 0.25 + 0.75 * Math.min(v / 0.35, 1) > 0.6;
      $$("text", e).forEach(t => (t.style.fill = light ? "#fff" : "var(--ink)"));
      $(".t1", e).textContent = fmt(v);
      $(".t2", e).textContent = "p " + pct(opt.det === "life" ? c.p_life : c.p_rule);
      e.classList.toggle("is-pay", isPay(c));
      e.dataset.pos = v > 0 ? 1 : 0;
      e.setAttribute("aria-label", label(c));
    };
    const label = c => `${c.regime}, ${c.arrival} traders per step, reaction ${c.react}, ${c.size} times wall: net ${fmt(c.net)} lots, after penalty ${fmt(value(c))}`;

    function build(wave) {
      panels.innerHTML = ""; cellEls = [];
      const regs = opt.regime === "both" ? ["calm", "volatile"] : [opt.regime];
      panels.classList.toggle("is-two", regs.length === 2);
      regs.forEach(reg => {
        const wrap = document.createElement("div"); wrap.className = "be-panel";
        wrap.innerHTML = `<h3>${reg === "calm" ? "Calm market" : "Volatile market"} · ${opt.size}× wall</h3>`;
        const W = L + 4 * (S + G6), H = T + 3 * (S + G6) + 46;
        const s = svg("svg", { viewBox: `0 0 ${W} ${H}` }, wrap);
        ARR.forEach((a, r) => { const t = svg("text", { x: L - 12, y: T + r * (S + G6) + S / 2 + 4, "text-anchor": "end", class: "ax" }, s); t.textContent = a; });
        RE.forEach((x, ci) => { const t = svg("text", { x: L + ci * (S + G6) + S / 2, y: T + 3 * (S + G6) + 14, "text-anchor": "middle", class: "ax" }, s); t.textContent = x; });
        const xl = svg("text", { x: L + 2 * (S + G6), y: H - 6, "text-anchor": "middle", class: "ax" }, s); xl.textContent = "how strongly traders react to the book →";
        const yl = svg("text", { x: 12, y: T + 1.5 * (S + G6), "text-anchor": "middle", class: "ax", transform: `rotate(-90 12 ${T + 1.5 * (S + G6)})` }, s); yl.textContent = "traders per step ↑";
        ARR.forEach((a, r) => RE.forEach((x, ci) => {
          const c = cellOf(a, x, reg, opt.size); if (!c) return;
          const g = svg("g", { class: "be-cell", tabindex: 0, role: "button" }, s);
          const x0 = L + ci * (S + G6), y0 = T + r * (S + G6);
          svg("rect", { x: x0, y: y0, width: S, height: S, class: "bg" }, g);
          svg("rect", { x: x0 - 1.5, y: y0 - 1.5, width: S + 3, height: S + 3, class: "ring" }, g);
          svg("text", { x: x0 + S / 2, y: y0 + S / 2 - 2, "text-anchor": "middle", class: "t1" }, g);
          svg("text", { x: x0 + S / 2, y: y0 + S / 2 + 15, "text-anchor": "middle", class: "t2" }, g);
          paint(g, c);
          if (wave && !reduced) { g.classList.add("wave"); g.style.animationDelay = (r + ci) * 70 + "ms"; }
          cellEls.push({ g, c, r, ci, svg: s, reg });
          g.addEventListener("pointermove", ev => showTip(c, ev.clientX, ev.clientY, ev.pointerType === "touch"));
          g.addEventListener("pointerleave", () => { if (!pinned) hideTip(); });
          g.addEventListener("focus", () => { const b = g.getBoundingClientRect(); showTip(c, b.right, b.top); });
          g.addEventListener("blur", hideTip);
          g.addEventListener("click", ev => { pinned = ev.pointerType === "touch" || pinned ? c : null; showTip(c, ev.clientX, ev.clientY); ev.stopPropagation(); });
        }));
        panels.appendChild(wrap);
      });
      contour(wave && !reduced ? 950 : 0);
      caption();
    }
    function contour(delay) {
      $$(".be-contour", panels).forEach(p => p.remove());
      const bySvg = new Map();
      cellEls.forEach(e => { if (!bySvg.has(e.svg)) bySvg.set(e.svg, []); bySvg.get(e.svg).push(e); });
      bySvg.forEach((list, s) => {
        const on = new Set(list.filter(e => isPay(e.c)).map(e => e.r + "," + e.ci));
        let d = "";
        const h = G6 / 2;
        on.forEach(k => {
          const [r, ci] = k.split(",").map(Number), x0 = L + ci * (S + G6) - h, y0 = T + r * (S + G6) - h, x1 = x0 + S + G6, y1 = y0 + S + G6;
          if (!on.has(r - 1 + "," + ci)) d += `M${x0},${y0}H${x1}`;
          if (!on.has(r + 1 + "," + ci)) d += `M${x0},${y1}H${x1}`;
          if (!on.has(r + "," + (ci - 1))) d += `M${x0},${y0}V${y1}`;
          if (!on.has(r + "," + (ci + 1))) d += `M${x1},${y0}V${y1}`;
        });
        if (!d) return;
        const p = svg("path", { d, class: "be-contour" }, s);
        if (delay) {
          const len = p.getTotalLength(); p.style.strokeDasharray = len; p.style.strokeDashoffset = len;
          setTimeout(() => { p.style.transition = "stroke-dashoffset 900ms cubic-bezier(0.23,1,0.32,1)"; p.style.strokeDashoffset = 0; }, delay);
        }
      });
    }
    function caption() {
      const n = cellEls.filter(e => isPay(e.c)).length;
      cap.innerHTML = `At F = ${opt.F.toFixed(2)}, <strong>${n}</strong> of the ${cellEls.length} conditions shown still reliably pay.`;
    }
    function setF(F) {
      opt.F = F; fIn.value = F; fOut.textContent = F.toFixed(2);
      fIn.style.setProperty("--fill", (F / 0.6) * 100 + "%");
      cellEls.forEach(e => {
        const was = e.g.dataset.pos, now = value(e.c) > 0 ? "1" : "0";
        if (was !== now && !reduced) {
          e.g.classList.remove("wave", "flip"); void e.g.getBoundingClientRect();
          e.g.style.animationDelay = e.ci * 40 + "ms"; e.g.classList.add("flip");
          e.g.dataset.pos = now;
          setTimeout(() => paint(e.g, e.c), 190 + e.ci * 40);
        } else paint(e.g, e.c);
      });
      contour(0); caption();
    }
    fIn.addEventListener("input", () => setF(+fIn.value));
    $("[data-sweep]").addEventListener("click", () => {
      const t0 = performance.now();
      const tick = now => { const k = reduced ? 1 : clamp((now - t0) / 3500, 0, 1); setF(Math.round(easeInOutSine(k) * 60) / 100); if (k < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    });
    fOut.textContent = "0.00"; fIn.style.setProperty("--fill", "0%");

    let pinned = null;
    function showTip(c, x, y) {
      const pR = c.p_rule, pL = c.p_life;
      tip.innerHTML = `<b>${c.regime === "calm" ? "Calm" : "Volatile"} · ${c.arrival} traders/step · react ${c.react} · ${c.size}× wall</b>`
        + `G ${fmt(c.G)} · U ${c.U.toFixed(2)} · net ${fmt(c.net)} (${fmt(c.net_lo)} to ${fmt(c.net_hi)})<br>`
        + `caught ${pct(pL)} (order-life), ${pct(pR)} (rule)<br>`
        + (c.net > 0 ? `F* = ${(c.net / (opt.det === "life" ? pL : pR)).toFixed(2)} lots` : "does not pay even with no penalty")
        + (c.net > 0 && !pays(c) ? "<br><i>interval includes zero: not reliable</i>" : "");
      tip.hidden = false;
      const r = tip.getBoundingClientRect();
      const tx = Math.min(x + 14, innerWidth - r.width - 8), ty = Math.min(y + 14, innerHeight - r.height - 8);
      tip.style.transform = `translate(${tx}px, ${ty}px)`;
    }
    function hideTip() { tip.hidden = true; pinned = null; }
    document.addEventListener("click", () => pinned && hideTip());
    addEventListener("scroll", () => !pinned && (tip.hidden = true), { passive: true });

    build(false);
    if (!reduced) { $$(".be-cell", panels).forEach(g => (g.style.opacity = 0)); $$(".be-contour", panels).forEach(p => (p.style.opacity = 0)); }
    inView(panels, () => { waved = true; build(true); }, 0.25);
  }

  /* =====================================================================
     4 · THE SEAL
     ===================================================================== */
  function seal() {
    const box = $("[data-envs]");
    const re = /(\d)\.\s+(\S+)\s+sealed:\s+(.+?)\s+sha256:\s+([0-9a-f]{64})/g;
    const items = []; let m;
    while ((m = re.exec(D.seal))) items.push({ file: m[2], when: m[3], hash: m[4] });
    const HEX = "0123456789abcdef";
    items.forEach((it, idx) => {
      const card = document.createElement("article"); card.className = "be-env";
      card.innerHTML = `<h3>${it.file}</h3><p class="be-env__date">Sealed ${it.when}</p>
        <p class="be-hash__label">Sealed fingerprint (SHA-256)</p><p class="be-hash" data-h></p>
        <button type="button" class="be-pill be-pill--ink" data-verify><i class="ph ph-seal-check"></i> Verify it yourself</button>
        <div data-checkwrap hidden><p class="be-hash__label" style="margin-top:1rem">Computed now, in your browser</p><p class="be-hash be-hash--check" data-c></p></div>
        <p class="be-verdict" data-v aria-live="polite"></p>`;
      // wax seal
      const wax = svg("svg", { viewBox: "0 0 60 60", class: "be-wax", "aria-hidden": "true" });
      const rnd = mulberry(11 + idx); let pts = "";
      for (let i = 0; i < 24; i++) { const a = (i / 24) * Math.PI * 2, r = 27 * (1 + (rnd() - 0.5) * 0.12); pts += `${30 + Math.cos(a) * r},${30 + Math.sin(a) * r} `; }
      svg("circle", { cx: 30, cy: 30, r: 28, class: "shock" }, wax);
      svg("polygon", { points: pts, class: "wax" }, wax);
      svg("circle", { cx: 30, cy: 30, r: 20, class: "inner" }, wax);
      const tx = svg("text", { x: 30, y: 36, "text-anchor": "middle" }, wax); tx.textContent = "EK";
      card.appendChild(wax);
      box.appendChild(card);
      const hp = $("[data-h]", card), chars = [];
      for (let g = 0; g < 8; g++) {
        const grp = document.createElement("span");
        for (let i = 0; i < 8; i++) { const c = document.createElement("i"); c.textContent = it.hash[g * 8 + i]; grp.appendChild(c); chars.push(c); }
        hp.appendChild(grp);
      }
      hp.setAttribute("aria-label", it.hash);
      if (reduced) { chars.forEach(c => c.classList.add("ok")); wax.style.opacity = 1; wax.style.transform = "rotate(-8deg)"; }
      else inView(card, () => {
        wax.classList.add("stamp");
        const t0 = performance.now();
        const tick = now => {
          let done = true;
          chars.forEach((c, i) => {
            if (c.classList.contains("ok")) return;
            if (now - t0 >= 200 + i * 22) { c.textContent = it.hash[i]; c.classList.add("ok"); }
            else { done = false; c.textContent = HEX[(Math.random() * 16) | 0]; }
          });
          if (!done) setTimeout(() => requestAnimationFrame(tick), 40);
        };
        requestAnimationFrame(tick);
      }, 0.4);

      $("[data-verify]", card).addEventListener("click", async () => {
        const out = $("[data-c]", card), v = $("[data-v]", card);
        $("[data-checkwrap]", card).hidden = false; out.innerHTML = ""; v.className = "be-verdict"; v.textContent = "Fetching and hashing…";
        let hex;
        try {
          const buf = await (await fetch(`research/${it.file}`, { cache: "no-store" })).arrayBuffer();
          hex = [...new Uint8Array(await crypto.subtle.digest("SHA-256", buf))].map(b => b.toString(16).padStart(2, "0")).join("");
        } catch (e) {
          v.textContent = "Could not fetch the file here. You can check it on GitHub: research/" + it.file; return;
        }
        let grp;
        for (let i = 0; i < 64; i++) {
          if (i % 8 === 0) { grp = document.createElement("span"); out.appendChild(grp); }
          const c = document.createElement("i"); c.textContent = hex[i];
          c.className = hex[i] === it.hash[i] ? "ok" : "bad"; grp.appendChild(c);
          if (!reduced) await new Promise(r => setTimeout(r, 18));
        }
        if (hex === it.hash) {
          v.classList.add("is-ok");
          v.innerHTML = `<svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M4 11.5l4.5 4.5L18 6"/></svg> Match: this file is unchanged since it was sealed.`;
        } else v.textContent = "Mismatch: the file served here differs from the sealed fingerprint.";
      });
    });
  }

  /* =====================================================================
     5 · BECKER CURVE   6 · CAREER CURVE
     ===================================================================== */
  function becker() {
    const s = $("[data-beckersvg]"), cap = $("[data-beckercap]");
    const L = 56, R = 584, T = 14, B = 336, PMAX = 1, FMAX = 3;
    const x = p => L + (p / PMAX) * (R - L), y = F => B - (F / FMAX) * (B - T);
    const ip = px => clamp((px - L) / (R - L), 0, 1) * PMAX, iF = py => clamp((B - py) / (B - T), 0, 1) * FMAX;
    const rDet = svg("path", { class: "r-det" }, s), rPay = svg("path", { class: "r-pay" }, s);
    for (let i = 0; i <= 4; i++) { svg("line", { x1: L, x2: R, y1: y(i * 0.75), y2: y(i * 0.75), class: "grid" }, s); const t = svg("text", { x: L - 8, y: y(i * 0.75) + 4, "text-anchor": "end" }, s); t.textContent = (i * 0.75).toFixed(2); }
    for (let i = 0; i <= 4; i++) { const t = svg("text", { x: x(i / 4), y: B + 18, "text-anchor": "middle" }, s); t.textContent = pct(i / 4); }
    svg("line", { x1: L, x2: R, y1: B, y2: B, class: "axis" }, s); svg("line", { x1: L, x2: L, y1: T, y2: B, class: "axis" }, s);
    const xl = svg("text", { x: (L + R) / 2, y: B + 38, "text-anchor": "middle" }, s); xl.textContent = "chance of being caught, p →";
    const yl = svg("text", { x: 14, y: (T + B) / 2, "text-anchor": "middle", transform: `rotate(-90 14 ${(T + B) / 2})` }, s); yl.textContent = "sanction F (lots) →";
    const lDet = svg("text", { class: "rlab", "text-anchor": "end" }, s); lDet.textContent = "DETERRED";
    const lPay = svg("text", { class: "rlab" }, s); lPay.textContent = "PAYS";
    const curve = svg("path", { class: "curve" }, s);
    D.cells.filter(pays).forEach(c => { const d = svg("circle", { cx: x(c.p_life), cy: y(c.Fstar_life), r: 5, class: "dot" }, s); const ti = svg("title", {}, d); ti.textContent = `${c.regime}, ${c.arrival}/step, react ${c.react}, ${c.size}×: F* ${c.Fstar_life.toFixed(2)} at p ${pct(c.p_life)}`; });
    const ripple = svg("circle", { class: "ripple", r: 8 }, s);
    const pt = svg("circle", { r: 9, class: "pt", tabindex: 0, role: "slider", "aria-label": "Regulator's catch rate and sanction. Arrow keys move it." }, s);
    let lastSide = null;
    const render = () => {
      const A = state.G - state.U - state.C;
      let d = "", top = `M${x(0.004)},${T}`, bot = "";
      if (A > 0) {
        const pts = [];
        for (let i = 0; i <= 120; i++) { const p = 0.004 + (i / 120) * (PMAX - 0.004); pts.push([x(p), y(Math.min(FMAX, A / p))]); }
        d = "M" + pts.map(q => q.join(",")).join("L");
        rDet.setAttribute("d", `M${pts[0][0]},${T}L` + pts.map(q => q.join(",")).join("L") + `L${R},${T}Z`);
        rPay.setAttribute("d", `M${pts[0][0]},${B}L` + pts.map(q => q.join(",")).join("L") + `L${R},${B}Z`);
        lPay.setAttribute("x", x(0.55)); lPay.setAttribute("y", Math.min(B - 10, y(A / 0.55) + 22));
        lPay.style.display = y(A / 0.55) + 22 < B ? "" : "none";
      } else {
        d = `M${L},${B}H${R}`; rDet.setAttribute("d", `M${L},${T}H${R}V${B}H${L}Z`); rPay.setAttribute("d", ""); lPay.style.display = "none";
      }
      lDet.setAttribute("x", R - 10); lDet.setAttribute("y", T + 22);
      curve.setAttribute("d", d);
      const px = x(state.p), py = y(Math.min(FMAX, state.F));
      pt.setAttribute("cx", px); pt.setAttribute("cy", py);
      const exp = state.p * state.F, deterred = exp >= A;
      if (lastSide !== null && lastSide !== deterred && !reduced) {
        ripple.setAttribute("cx", px); ripple.setAttribute("cy", py); ripple.classList.remove("go"); void ripple.getBoundingClientRect(); ripple.classList.add("go");
      }
      lastSide = deterred;
      cap.innerHTML = A <= 0 ? "With these values it doesn’t pay at any penalty."
        : `Expected penalty pF = <strong>${exp.toFixed(2)}</strong> vs gain G − U − C = <strong>${A.toFixed(2)}</strong> → ${deterred ? "deterred" : "<strong>still pays</strong>"}`;
      pt.setAttribute("aria-valuetext", `p ${pct(state.p)}, F ${state.F.toFixed(2)}`);
    };
    subs.push(render);
    // drag the regulator's point
    let drag = false;
    const move = ev => {
      const r = s.getBoundingClientRect(), sx = 600 / r.width, sy = 380 / r.height;
      state.p = +ip((ev.clientX - r.left) * sx).toFixed(2); state.F = +iF((ev.clientY - r.top) * sy).toFixed(2); emit();
    };
    pt.addEventListener("pointerdown", ev => { drag = true; pt.setPointerCapture(ev.pointerId); });
    pt.addEventListener("pointermove", ev => drag && move(ev));
    pt.addEventListener("pointerup", () => (drag = false));
    pt.addEventListener("keydown", ev => {
      const k = { ArrowLeft: ["p", -0.02], ArrowRight: ["p", 0.02], ArrowUp: ["F", 0.05], ArrowDown: ["F", -0.05] }[ev.key];
      if (!k) return; ev.preventDefault();
      state[k[0]] = clamp(+(state[k[0]] + k[1]).toFixed(2), 0, k[0] === "p" ? 1 : 3); emit();
    });
    inView(s, () => {
      if (reduced) return;
      const len = curve.getTotalLength(); curve.style.strokeDasharray = len; curve.style.strokeDashoffset = len;
      requestAnimationFrame(() => { curve.style.transition = "stroke-dashoffset 1200ms cubic-bezier(0.23,1,0.32,1)"; curve.style.strokeDashoffset = 0; });
      setTimeout(() => { curve.style.strokeDasharray = ""; curve.style.transition = ""; }, 1300);
    }, 0.4);
  }

  function career() {
    const s = $("[data-careersvg]");
    const L = 56, R = 560, T = 14, B = 336, N = 50;
    const x = n => L + ((n - 1) / (N - 1)) * (R - L), y = v => B - v * (B - T);
    for (let i = 0; i <= 4; i++) { svg("line", { x1: L, x2: R, y1: y(i / 4), y2: y(i / 4), class: "grid" }, s); const t = svg("text", { x: L - 8, y: y(i / 4) + 4, "text-anchor": "end" }, s); t.textContent = pct(i / 4); }
    [1, 10, 20, 30, 40, 50].forEach(n => { const t = svg("text", { x: x(n), y: B + 18, "text-anchor": "middle" }, s); t.textContent = n; });
    svg("line", { x1: L, x2: R, y1: B, y2: B, class: "axis" }, s);
    const xl = svg("text", { x: (L + R) / 2, y: B + 38, "text-anchor": "middle" }, s); xl.textContent = "number of attempts, N →";
    const curveFor = p => Array.from({ length: N }, (_, i) => 1 - Math.pow(1 - p, i + 1));
    const pathOf = v => "M" + v.map((q, i) => `${x(i + 1)},${y(q)}`).join("L");
    [0.05, 0.2].forEach(p => {
      svg("path", { d: pathOf(curveFor(p)), class: "ln" }, s);
      const v = curveFor(p), t = svg("text", { x: R + 6, y: y(v[N - 1]) + 4, class: "lnlab" }, s); t.textContent = "p " + pct(p);
    });
    const live = svg("path", { class: "ln live" }, s), lab = svg("text", { x: R + 6, class: "lnlab" }, s);
    let cur = curveFor(state.p), goal = cur, raf = 0;
    const draw = () => {
      let moving = false;
      cur = cur.map((v, i) => { const nv = reduced ? goal[i] : lerp(v, goal[i], 0.15); if (Math.abs(nv - goal[i]) > 1e-4) moving = true; return nv; });
      live.setAttribute("d", pathOf(cur)); lab.setAttribute("y", y(cur[N - 1]) + (cur[N - 1] > 0.97 ? 14 : 4)); lab.textContent = "p " + pct(state.p);
      raf = moving ? requestAnimationFrame(draw) : 0;
    };
    subs.push(() => { goal = curveFor(state.p); if (!raf) raf = requestAnimationFrame(draw); });
  }

  function marquee() {
    const paying = D.cells.filter(pays), fmax = Math.max(...paying.map(c => c.Fstar_life));
    const nof = D.cells.filter(c => c.react === 0);
    const facts = [`${paying.length} of ${D.cells.length} conditions reliably paid`, `no one reading the book → paid in ${nof.filter(pays).length} of ${nof.length}`,
      "volatile markets hit the wall", `break-even sanction ≤ ${fmax.toFixed(2)} lots`, "predictions sealed with SHA-256", "held-out seeds untouched"];
    const html = facts.map(f => `<span>${f}</span><b>•</b>`).join("");
    $("[data-marquee]").innerHTML = html + html;
  }

  if (!D) { console.warn("breakeven.js: no data"); return; }
  hero(); equation(); map(); seal(); becker(); career(); marquee();
  emit();
})();
