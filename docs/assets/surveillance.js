/* Surveillance Lab. Every number drawn here comes from data/surveillance.js (build_surveillance.py)
   or data/breakeven.js (run_breakeven.py). Nothing is typed in by hand except text. */
(function () {
  "use strict";
  var S = window.SURVEILLANCE;
  if (!S) return;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var EASE = "cubic-bezier(0.23, 1, 0.32, 1)";
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var topOf = function (el) { return el.getBoundingClientRect().top + window.scrollY; };
  var clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
  var pct = function (arr, thr) { return arr.length ? Math.round(100 * arr.filter(function (v) { return v > 0 && v >= thr; }).length / arr.length) : 0; };
  var NS = "http://www.w3.org/2000/svg";
  function svgEl(name, attrs, parent) {
    var el = document.createElementNS(NS, name);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
  }
  function countUp(el, to, opts) {
    opts = opts || {};
    var dec = opts.dec || 0, fmt = opts.fmt || "{}", dur = reduce ? 0 : (opts.dur || 1400);
    var t0 = performance.now();
    function frame(now) {
      var k = dur ? clamp((now - t0) / dur, 0, 1) : 1;
      var e = k === 1 ? 1 : 1 - Math.pow(2, -10 * k);
      el.textContent = fmt.replace("{}", (to * e).toFixed(dec));
      if (k < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  var tokens = {};
  function readTokens() {
    var cs = getComputedStyle(document.documentElement);
    ["--paper", "--ink", "--ink-2", "--ink-3", "--mark", "--bid", "--ask", "--line"].forEach(function (n) { tokens[n] = cs.getPropertyValue(n).trim(); });
  }
  readTokens();
  new MutationObserver(readTokens).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", readTokens);

  /* ---------- 1. Hero ---------- */
  var hero = $("[data-hero]");
  var canvas = $("[data-hero-book]");
  var heroText = $("[data-hero-text]");
  var cue = $("[data-cue]");
  var l2 = $("[data-l2]");
  l2.innerHTML = l2.textContent.split("").map(function (c) { return '<span class="ch">' + (c === " " ? "&nbsp;" : c) + "</span>"; }).join("");

  $$("[data-count]").forEach(function (dd) {
    var v = pct(S.scores[dd.dataset.count] || [], S.threshold);
    dd.dataset.value = v;
    if (reduce) dd.textContent = v + "%";
  });

  function entrance() {
    var ins = $$("[data-in]", hero);
    if (reduce) { canvas.style.opacity = 1; return; }
    var fade = function (el, delay, y) {
      return el.animate([{ opacity: 0, transform: "translateY(" + (y || 12) + "px)" }, { opacity: 1, transform: "none" }],
        { duration: 700, delay: delay, easing: EASE, fill: "both" });
    };
    canvas.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 1600, delay: 200, easing: "ease-out", fill: "both" });
    fade(ins[0], 0, 8);
    $("[data-l1]").animate([{ transform: "translateY(105%)" }, { transform: "none" }], { duration: 900, delay: 120, easing: EASE, fill: "both" });
    $$(".ch", l2).forEach(function (ch, i) {
      ch.animate([{ transform: "translateY(110%) rotate(4deg)" }, { transform: "none" }], { duration: 820, delay: 260 + i * 34, easing: EASE, fill: "both" });
    });
    fade(ins[1], 680); fade(ins[2], 800); fade(ins[3], 870);
    $$(".sv-stats > div", hero).forEach(function (d, i) {
      fade(d, 1000 + i * 80);
      var dd = $("dd", d);
      setTimeout(function () { countUp(dd, +dd.dataset.value, { fmt: "{}%" }); }, 1000 + i * 80);
    });
    fade(ins[ins.length - 1], 1240);
  }
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(entrance);

  // The order book, breathing: the real spoof replay on a loop.
  var ctx = canvas.getContext("2d");
  var frames = S.spoof.frames, nRows = S.prices.length;
  var cur = frames[0].rows.map(function () { return [0, 0, 0]; });
  var W = 0, H = 0, dpr = 1;
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
  }
  resize();
  new ResizeObserver(resize).observe(canvas);
  function rgba(color, a) { return "color-mix(in srgb, " + color + " " + Math.round(a * 100) + "%, transparent)"; }
  function draw(fr, dt) {
    var k = 1 - Math.exp(-dt * 9);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    var axis = W < 760 ? W * 0.5 : W * 0.62, span = H * 0.7, top = (H - span) / 2, pitch = span / nRows, bh = pitch * 0.38;
    var unit = (W < 760 ? 0.44 : 0.34) * W / 60;
    var soft = W < 760 ? 0.55 : 1;
    var bidC = rgba(tokens["--bid"], 0.2 * soft), askC = rgba(tokens["--ask"], 0.22 * soft), wallC = rgba(tokens["--mark"], 0.6 * soft);
    fr.rows.forEach(function (r, i) {
      var c = cur[i];
      c[0] += ((r[0] - r[2]) - c[0]) * k; c[1] += (r[1] - c[1]) * k; c[2] += (r[2] - c[2]) * k;
      var y = top + i * pitch + (pitch - bh) / 2;
      ctx.fillStyle = bidC; roundRect(axis - c[0] * unit, y, c[0] * unit, bh);
      ctx.fillStyle = wallC; roundRect(axis - (c[0] + c[2]) * unit, y, c[2] * unit, bh);
      ctx.fillStyle = askC; roundRect(axis + 6, y, c[1] * unit, bh);
    });
  }
  function roundRect(x, y, w, h) {
    if (w < 0.5) return;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x, y, w, h, 3); else ctx.rect(x, y, w, h);
    ctx.fill();
  }
  var hi = 0, heroVisible = true, last = performance.now(), acc = 0, hold = 0;
  if (reduce) {
    var biggest = frames.reduce(function (b, f, i) { var w = f.rows.reduce(function (s, r) { return s + r[2]; }, 0); return w > b[0] ? [w, i] : b; }, [-1, 0])[1];
    for (var n = 0; n < 40; n++) draw(frames[biggest], 1);
  } else {
    new IntersectionObserver(function (e) { heroVisible = e[0].isIntersecting; }).observe(hero);
    (function loop(now) {
      var dt = Math.min(0.05, (now - last) / 1000); last = now;
      if (heroVisible) {
        if (hold > 0) hold -= dt;
        else { acc += dt; if (acc > 0.2) { acc = 0; hi++; if (hi >= frames.length) { hi = 0; hold = 1.2; } } }
        draw(frames[hi], dt);
      }
      requestAnimationFrame(loop);
    })(last);
  }

  /* ---------- 2. Twin replay ---------- */
  var replay = $("[data-replay]");
  var nF = S.spoof.frames.length;
  var maxQ = 0;
  [S.spoof, S.reversal].forEach(function (ep) { ep.frames.forEach(function (f) { f.rows.forEach(function (r) { maxQ = Math.max(maxQ, r[0], r[1]); }); }); });
  var scaleQ = function (q) { return clamp(q / maxQ, 0, 1); };
  var CLAUSES = ["Showed buying interest", "Withdrew it", "Traded the other way"];
  var twins = $$("[data-twin]").map(function (card) {
    var ep = S[card.dataset.twin];
    var ladder = $("[data-ladder]", card);
    var rows = S.prices.map(function (p) {
      var row = document.createElement("div");
      row.className = "sv-row";
      row.innerHTML = '<div class="sv-cell sv-cell--bid"><span class="sv-bar sv-bar--depth"></span><span class="sv-bar sv-bar--wall"></span></div>' +
        '<span class="sv-px">' + p + '</span><div class="sv-cell sv-cell--ask"><span class="sv-bar sv-bar--depth"></span><span class="sv-bar sv-bar--own"></span></div>';
      ladder.appendChild(row);
      var b = $$(".sv-bar", row);
      return { el: row, bid: b[0], wall: b[1], ask: b[2], own: b[3] };
    });
    var list = $("[data-clauses]", card);
    var items = CLAUSES.map(function (txt, i) {
      var li = document.createElement("li");
      li.innerHTML = "<i></i><span>" + (i + 1) + "&nbsp; " + txt + "</span><b>0 lots</b>";
      list.appendChild(li);
      return li;
    });
    $("[data-thr]", card).textContent = S.threshold;
    $(".sv-meter__tick", card).style.left = "calc((100% - 64px) * " + (S.threshold / 50) + ")";
    $(".sv-meter__lbl", card).style.left = "calc((100% - 64px) * " + (S.threshold / 50) + ")";
    return { card: card, ep: ep, rows: rows, items: items, fill: $("[data-fill]", card) };
  });
  function render(idx) {
    twins.forEach(function (tw) {
      var f = tw.ep.frames[idx], cl = tw.ep.clauses[idx];
      f.rows.forEach(function (r, i) {
        var R = tw.rows[i], depth = r[0] - r[2];
        // the wall sits outermost: depth fills from the centre, the wall extends beyond it
        R.bid.style.transform = "scaleX(" + scaleQ(depth) + ")";
        R.wall.style.transform = "scaleX(" + scaleQ(r[0]) + ")";
        R.wall.style.clipPath = "inset(0 " + (r[0] ? depth / r[0] * 100 : 0) + "% 0 0)";
        R.ask.style.transform = "scaleX(" + scaleQ(r[1] - r[3]) + ")";
        R.own.style.transform = "scaleX(" + scaleQ(r[1]) + ")";
        R.own.style.clipPath = "inset(0 0 0 " + (r[1] ? (r[1] - r[3]) / r[1] * 100 : 0) + "%)";
        R.el.classList.toggle("is-touch", S.prices[i] === f.bb || S.prices[i] === f.ba);
      });
      tw.items.forEach(function (li, i) {
        li.classList.toggle("is-on", cl[i] > 0);
        $("b", li).textContent = cl[i] + " lots";
      });
      tw.fill.style.transform = "scaleX(" + clamp(cl[3] / 50, 0, 1) + ")";
      tw.card.classList.toggle("is-alert", cl[3] >= S.threshold);
    });
    var t = S.spoof.frames[idx].t;
    $("[data-step]").textContent = "step " + t + " · t" + (t - S.spoof.start >= 0 ? "+" : "") + (t - S.spoof.start);
    head.style.left = (idx / (nF - 1) * 100) + "%";
    setCaption(t);
  }
  var head = $("[data-head]"), track = $("[data-track]");
  var t0 = S.spoof.frames[0].t;
  function pin(t, kind, label) {
    var p = document.createElement("span");
    p.className = "sv-pin sv-pin--" + kind;
    p.style.left = ((t - t0) / (nF - 1) * 100) + "%";
    p.innerHTML = "<span>" + label + "</span>";
    track.appendChild(p);
  }
  pin(S.spoof.start, "spoof", "wall placed");
  if (S.spoof.fill_time != null && S.spoof.fill_time !== S.spoof.end) pin(S.spoof.fill_time, "spoof", "sell fills");
  pin(S.spoof.end, "spoof", S.spoof.fill_time === S.spoof.end ? "sell fills · wall cancelled" : "wall cancelled");
  pin(S.reversal.start, "reversal", "order placed");
  pin(S.reversal.end, "reversal", "changes mind: cancel + sell");
  var CAPS = [
    "Before: an ordinary order book. Nobody has done anything yet.",
    "Both traders place a " + S.wall + "-lot buy order behind the best bid. Only one of them never meant it to trade.",
    "The spoofer: the small sell fills and the wall is cancelled at once. The honest trader: the order is still resting.",
    "The honest trader: news arrives. They cancel and sell " + S.typical + " lots. Both accounts now read the same: showed, withdrew, sold the other way. Both alert."
  ];
  var caption = $("[data-caption]"), capIdx = -1;
  function setCaption(t) {
    var i = t < S.spoof.start ? 0 : t < S.spoof.end ? 1 : t < S.reversal.end ? 2 : 3;
    if (i === capIdx) return;
    capIdx = i;
    if (reduce) { caption.textContent = CAPS[i]; return; }
    caption.animate([{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateY(-4px)" }], { duration: 160, easing: "ease-in" }).onfinish = function () {
      caption.textContent = CAPS[i];
      caption.animate([{ opacity: 0, transform: "translateY(6px)" }, { opacity: 1, transform: "none" }], { duration: 260, easing: EASE });
    };
  }
  $("[data-seed]").textContent = "Real simulator episodes from seed " + S.seed + ": the same market, run twice. Calm market, " + S.size_mult + "× orders (" + S.wall + " lots).";

  // jump straight to frame i (the site scrolls smoothly by default, which would lag behind)
  function jump(i) { window.scrollTo({ top: topOf(replay) + (i / (nF - 1)) * (replay.offsetHeight - innerHeight), behavior: "instant" }); }
  var curIdx = -1;
  function show(idx) { idx = clamp(idx, 0, nF - 1); if (idx !== curIdx) { curIdx = idx; render(idx); scrub.value = idx; } }
  var scrub = $("[data-scrub]");
  scrub.max = nF - 1;
  scrub.addEventListener("input", function () { show(+scrub.value); });
  function progress() {
    var r = replay.getBoundingClientRect();
    return clamp(-r.top / (replay.offsetHeight - innerHeight), 0, 1);
  }
  show(0);

  // mobile: choose which twin is shown
  $$("[data-show]").forEach(function (b) {
    b.addEventListener("click", function () {
      $$("[data-show]").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
      twins.forEach(function (tw) { tw.card.classList.toggle("is-shown", tw.card.dataset.twin === b.dataset.show); });
    });
  });
  twins[0].card.classList.add("is-shown");

  // play: scroll through the section at 6 steps a second
  var playBtn = $("[data-play]"), playing = null;
  function stop() { if (playing) { clearInterval(playing); playing = null; playBtn.textContent = "Play"; } }
  playBtn.addEventListener("click", function () {
    if (playing) return stop();
    var i = curIdx >= nF - 1 ? 0 : curIdx;
    playBtn.textContent = "Pause";
    playing = setInterval(function () {
      i++;
      if (i >= nF) return stop();
      if (reduce) show(i);
      else jump(i);
    }, 1000 / 6);
  });
  ["wheel", "touchstart"].forEach(function (ev) { window.addEventListener(ev, stop, { passive: true }); });
  replay.addEventListener("keydown", function (e) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault(); stop();
    var i = clamp(curIdx + (e.key === "ArrowRight" ? 1 : -1), 0, nF - 1);
    if (reduce) show(i); else jump(i);
  });

  /* ---------- 3. The dial ---------- */
  var plot = $("[data-plot]");
  var ROWS = [["spoof", "Spoofs", "var(--mark)"], ["layer", "Layered spoofs", "var(--mark)"], ["reversal", "Honest: changed mind", "var(--ink)"],
              ["withdrawal", "Honest: quick withdrawal", "var(--ink-2)"], ["control", "Honest: genuine large order", "var(--ink-2)"]];
  var BAND = 92, X0 = 260, X1 = 840, XMAX = 50, VB_H = ROWS.length * BAND + 50;
  var xs = function (v) { return X0 + (v / XMAX) * (X1 - X0); };
  plot.setAttribute("viewBox", "0 0 1000 " + VB_H);
  var size = 16, thr = S.threshold, dots = [], outs = [], dialIn = false;
  var gGrid = svgEl("g", {}, plot), gRows = svgEl("g", {}, plot), gDots = svgEl("g", {}, plot), gLine = svgEl("g", {}, plot);
  [0, 10, 20, 30, 40, 50].forEach(function (v) {
    svgEl("line", { x1: xs(v), x2: xs(v), y1: 6, y2: ROWS.length * BAND, class: "grid", "stroke-opacity": 0.6 }, gGrid);
    svgEl("text", { x: xs(v), y: ROWS.length * BAND + 22, class: "ax", "text-anchor": "middle" }, gGrid).textContent = v;
  });
  svgEl("text", { x: X1, y: ROWS.length * BAND + 42, class: "ax", "text-anchor": "end" }, gGrid).textContent = "score (lots) →";
  var calX = xs(S.threshold);
  svgEl("line", { x1: calX, x2: calX, y1: ROWS.length * BAND, y2: ROWS.length * BAND + 8, class: "cal" }, gGrid);
  svgEl("text", { x: calX + 6, y: ROWS.length * BAND + 34, class: "callbl" }, gGrid).textContent = "calibrated";
  ROWS.forEach(function (r, i) {
    var y = i * BAND + BAND / 2;
    svgEl("text", { x: 0, y: y - 2, class: "rlbl" }, gRows).textContent = r[1];
    var c = svgEl("text", { x: 0, y: y + 16, class: "rcount" }, gRows);
    var o = svgEl("text", { x: 1000, y: y + 5, class: "rout", "text-anchor": "end" }, gRows);
    outs.push({ count: c, out: o, shown: -1 });
  });
  var line = svgEl("line", { y1: 0, y2: ROWS.length * BAND, class: "line" }, gLine);
  var handle = svgEl("circle", { cy: 0, r: 7, class: "handle", tabindex: -1 }, gLine);
  var hlbl = svgEl("text", { y: -14, class: "hlbl", "text-anchor": "middle" }, gLine);

  function buildDots() {
    gDots.textContent = ""; dots = [];
    ROWS.forEach(function (r, i) {
      var vals = S.scores[r[0] + "_" + size] || [];
      var groups = {};
      vals.forEach(function (v) { (groups[v] = groups[v] || []).push(v); });
      outs[i].count.textContent = vals.length + " episodes";
      Object.keys(groups).forEach(function (key) {
        var v = +key, g = groups[key], cols = Math.ceil(g.length / 9);
        var left = Math.max(X0 + 4, xs(v) - (cols - 1) * 4.5);
        g.forEach(function (_, k) {
          var col = Math.floor(k / 9), m = k % 9, off = (m % 2 ? 1 : -1) * Math.ceil(m / 2) * 9;
          var cx = left + col * 9 + (m % 2 ? 4.5 : 0), cy = i * BAND + BAND / 2 + off;
          var d = svgEl("circle", { cx: cx, cy: cy, r: 4.2, class: "d", stroke: r[2] }, gDots);
          d.style.stroke = r[2];
          dots.push({ el: d, v: v, row: i, cx: cx });
        });
      });
    });
    paint();
  }
  function paint() {
    var x = xs(thr);
    line.setAttribute("x1", x); line.setAttribute("x2", x);
    handle.setAttribute("cx", x); hlbl.setAttribute("x", x);
    hlbl.textContent = "alarm at " + thr + " lots";
    dots.forEach(function (d) {
      var on = d.v > 0 && d.v >= thr;
      d.el.style.fill = on ? ROWS[d.row][2] : "var(--paper)";
    });
    var rates = ROWS.map(function (r, i) {
      var vals = S.scores[r[0] + "_" + size] || [], p = pct(vals, thr), n = Math.round(p * vals.length / 100);
      var hits = vals.filter(function (v) { return v > 0 && v >= thr; }).length;
      outs[i].out.textContent = hits + " / " + vals.length + " · " + p + "%";
      return p;
    });
    var a = rates[0], b = rates[1], c = rates[2];
    var txt = "At " + thr + " lots you catch " + a + "% of spoofs and " + b + "% of layered spoofs, and you wrongly flag " + c + "% of honest traders who changed their mind.";
    var same = (a === 0 && c === 0) || (a > 70 && c > 70);
    readout.innerHTML = txt + (same ? "<span>Spoofs and changes of mind move together. Both score the full size of the withdrawn order, so no line can split them.</span>" : "");
    thrInput.value = thr; thrOut.textContent = thr;
  }
  var readout = $("[data-readout]"), thrInput = $("[data-thr-input]"), thrOut = $("[data-thr-out]");
  thrInput.min = 1;
  thrInput.addEventListener("input", function () { thr = +thrInput.value; paint(); });
  function fromPointer(e) {
    var pt = plot.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    var p = pt.matrixTransform(plot.getScreenCTM().inverse());
    thr = Math.round(clamp((p.x - X0) / (X1 - X0) * XMAX, 1, XMAX));
    paint();
  }
  var dragging = false;
  plot.addEventListener("pointerdown", function (e) { dragging = true; plot.setPointerCapture(e.pointerId); fromPointer(e); });
  plot.addEventListener("pointermove", function (e) { if (dragging) fromPointer(e); });
  plot.addEventListener("pointerup", function () { dragging = false; });
  $$("[data-size]").forEach(function (b) {
    b.addEventListener("click", function () {
      size = +b.dataset.size;
      $$("[data-size]").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
      buildDots(); if (dialIn) dots.forEach(function (d) { d.el.style.opacity = 1; });
    });
  });
  buildDots();
  if (!reduce) {
    dots.forEach(function (d) { d.el.style.opacity = 0; });
    gLine.style.opacity = 0;
  }
  new IntersectionObserver(function (e, obs) {
    if (!e[0].isIntersecting) return;
    obs.disconnect(); dialIn = true;
    if (reduce) return;
    dots.forEach(function (d, i) {
      d.el.animate([{ transform: "translateX(" + (X0 - d.cx) + "px)", opacity: 0 }, { transform: "none", opacity: 1 }],
        { duration: 700, delay: i * 4, easing: EASE, fill: "forwards" }).onfinish = function () { d.el.style.opacity = 1; };
    });
    var target = thr; thr = XMAX; paint();
    gLine.style.opacity = 1;
    var tStart = performance.now() + 500;
    (function slide(now) {
      var k = clamp((now - tStart) / 900, 0, 1), e2 = 1 - Math.pow(1 - k, 3);
      thr = Math.round(XMAX + (target - XMAX) * e2); paint();
      if (k < 1) requestAnimationFrame(slide);
    })(performance.now());
  }, { threshold: 0.25 }).observe($("[data-dial]"));

  /* ---------- 4. Economics stack ---------- */
  var B = window.BREAKEVEN;
  if (B && B.cells) {
    var heat = $("[data-heat]");
    var order = B.cells.slice().sort(function (a, b) { return a.size - b.size || a.regime.localeCompare(b.regime) || a.arrival - b.arrival || a.react - b.react; });
    order.forEach(function (c) {
      var i = document.createElement("i");
      i.className = c.pays === "yes" ? "y" : c.pays === "unclear" ? "u" : "";
      i.title = c.size + "×, " + c.regime + ", liquidity " + c.arrival + ", responsiveness " + c.react + ": " + c.pays;
      heat.appendChild(i);
    });
    var cap = document.createElement("p");
    cap.textContent = "Rows, top to bottom: 8× calm, 8× volatile, 16× calm, 16× volatile. Within a row: liquidity, then book responsiveness, rising to the right. Magenta: pays · outlined: unclear · plain: does not pay.";
    heat.appendChild(cap);
    $("[data-pays]").textContent = B.cells.filter(function (c) { return c.pays === "yes"; }).length;
    $("[data-volneg]").textContent = B.cells.filter(function (c) { return c.regime === "volatile" && c.pays === "no"; }).length;
  }
  var cards = $$(".sv-card");
  var activate = {
    effect: function (c) {
      $$(".bar", c).forEach(function (r) { r.animate([{ width: 0 }, { width: r.dataset.w + "px" }], { duration: reduce ? 0 : 900, easing: EASE, fill: "forwards" }); r.setAttribute("width", r.dataset.w); });
      $$(".v", c).forEach(function (t) { t.setAttribute("x", +t.dataset.at + 8); });
    },
    pays: function (c) {
      var cells = $$(".sv-heat i", c);
      cells.forEach(function (i, k) { i.style.transitionDelay = (reduce ? 0 : Math.floor(k / 12) * 120 + (k % 12) * 12) + "ms"; });
      $(".sv-heat", c).classList.add("is-in");
    },
    proof: function (c) {
      $("[data-needle]", c).animate([{ transform: "rotate(-90deg)" }, { transform: "rotate(0deg)" }], { duration: reduce ? 0 : 1100, easing: EASE, fill: "forwards" });
    },
    model: function (c) {
      var eq = $("[data-eq]", c), spans = $$(".sv-eq__line span", eq);
      spans.forEach(function (s, i) { s.style.transitionDelay = (reduce ? 0 : i * 140) + "ms"; });
      eq.classList.add("is-in");
    }
  };
  var cardObs = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      cardObs.unobserve(e.target);
      var c = e.target;
      activate[c.dataset.card](c);
      var num = $("[data-num]", c);
      if (num) countUp(num, +num.dataset.num, { dec: +(num.dataset.dec || 0), fmt: num.dataset.fmt, dur: 1300 });
    });
  }, { threshold: 0.45 });
  cards.forEach(function (c) { cardObs.observe(c); });

  /* ---------- One scroll handler ---------- */
  var items = $$(".sv-stack__item"), ticking = false;
  function onScroll() {
    ticking = false;
    var p = clamp(scrollY / hero.offsetHeight, 0, 1);
    if (!reduce) {
      canvas.style.transform = "translateY(" + (p * 35) + "%)";
      canvas.style.filter = "opacity(" + clamp(1 - p * 1.25, 0, 1) + ")";
      heroText.style.transform = "scale(" + (1 - p * 0.04) + ")";
      heroText.style.opacity = clamp(1 - p * 1.4, 0, 1);
      cue.style.opacity = clamp(1 - p * 4, 0, 1);
      show(Math.round(progress() * (nF - 1)));
      if (innerWidth > 900) {
        items.forEach(function (it, i) {
          var next = items[i + 1], card = it.firstElementChild;
          if (!next) return;
          var stickTop = 96 + (i + 1) * 22, nt = next.getBoundingClientRect().top;
          var k = clamp((innerHeight - nt) / (innerHeight - stickTop), 0, 1);
          card.style.transform = "scale(" + (1 - k * (items.length - 1 - i) * 0.035) + ")";
          card.querySelector(".sv-card__body").style.opacity = 1 - k * 0.45;
        });
      }
    }
  }
  window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();
})();
