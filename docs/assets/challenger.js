/* Chapter 4: the AI challenger (Part 4) and the surveillance desk (Part 5).
   Every number comes from window.TEACHING (written by build_site.py from results/challenger*.csv,
   thresholds.csv and alert_budget.csv). Nothing here is typed by hand. */
(() => {
  const T = window.TEACHING || {};
  if (!T.challenger) return;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs = {}, parent, text) => {
    const n = tag === "svg" || ["g", "line", "circle", "path", "text", "rect", "polyline"].includes(tag)
      ? document.createElementNS(NS, tag) : document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    if (text !== undefined) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };
  const pct = (v, d = 0) => (v === undefined || v === null || Number.isNaN(v) ? "n/a" : `${(v * 100).toFixed(d)}%`);
  const lots = (v) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2)}`;

  const C = T.challenger;
  const TARGETS = ["nobody", "rule", "window", "order-life", "seen", "both"].filter((t) => C.some((r) => r.target === t));
  const NAME = { nobody: "No surveillance", rule: "The rule", window: "Legal definition, 40-step windows",
    "order-life": "Legal definition, each order's life", seen: "Legal definition, as the market sees it", both: "Both versions together" };
  const SHORT = { nobody: "nobody", rule: "the rule", window: "the windowed definition", "order-life": "the order-life definition",
    seen: "the 'as the market sees it' definition", both: "both versions together" };
  const COLOUR = { nobody: "var(--ink-3)", rule: "var(--det-rule)", window: "var(--det-pca)", "order-life": "var(--mark)", seen: "var(--det-iforest)", both: "#7b61d9" };
  const DETS = ["rule", "window", "order-life", "seen", "both"];

  const plain = (t) => C.find((r) => r.target === t && r.rank === 0);
  const best = (t) => C.filter((r) => r.target === t && r.rank > 0).sort((a, b) => b.payoff - a.payoff)[0];
  const honest = (cas, det, m) => (T.challenger_honest || []).find((r) => r.case === cas && r.detector === det && (m === undefined || r.size_mult === m));

  // ---- numbers in the text ------------------------------------------------------------------
  const N = {};
  TARGETS.forEach((t) => {
    const k = t.replace("-", "");
    N[`best_${k}`] = lots(best(t).payoff);
    N[`plain_${k}`] = lots(plain(t).payoff);
    N[`bestgain_${k}`] = lots(best(t).gain);
    N[`beststrat_${k}`] = best(t).strategy;
    DETS.forEach((d) => { N[`bestcaught_${k}_${d.replace("-", "")}`] = pct(best(t)[`caught_${d}`]); });
  });
  N.plaingain = lots(plain("nobody").gain);
  const share = (t) => Math.max(0, best(t).payoff) / Math.max(1e-9, best("nobody").payoff);
  TARGETS.forEach((t) => { N[`keeps_${t.replace("-", "")}`] = pct(share(t)); });
  const vis = T.visibility || [];
  N.vis5 = pct((vis.find((r) => r.ticks_behind_best === 5) || {}).weight);
  N.vis6 = pct((vis.find((r) => r.ticks_behind_best === 6) || {}).weight, 0);
  ["order-life", "seen", "window", "rule", "both"].forEach((d) => {
    const k = d.replace("-", "");
    const h = (c, m) => (honest(c, d, m) || {}).value;
    N[`skew16_${k}`] = pct(h("market maker working off a position", 16));
    N[`skew8_${k}`] = pct(h("market maker working off a position", 8));
    N[`spoof16_${k}`] = pct(h("spoof", 16));
    N[`spoof8_${k}`] = pct(h("spoof", 8));
    N[`layer16_${k}`] = pct(h("layered spoof", 16));
    N[`gen16_${k}`] = pct(h("honest large order", 16));
    N[`wd16_${k}`] = pct(h("honest quick cancel", 16));
    N[`rev16_${k}`] = pct(h("honest change of mind", 16));
    N[`fpr_${k}`] = pct(h("normal calm market"), 1);
    N[`fprvol_${k}`] = pct(h("normal volatile market"), 1);
  });
  // Part 5
  const TH = T.thresholds || [];
  const th = (det, mode, test, metric, m) => (TH.find((r) => r.detector === det && r.mode === mode && r.test === test && r.metric === metric &&
    (m === undefined ? r.size_mult === undefined : r.size_mult === m)) || {}).value;
  const UNTAUGHT = ["PCA (generic)", "IForest (generic)", "Seq-PCA (generic)", "LSTM-AE (generic)"];
  const range = (vals, d = 0) => { const v = vals.filter((x) => x !== undefined); return v.length ? `${pct(Math.min(...v), d)}–${pct(Math.max(...v), d)}` : "n/a"; };
  N.volFixed = range(UNTAUGHT.map((d) => th(d, "fixed", "normal_volatile", "false_alarm_rate")), 1);
  N.volAdapt = range(UNTAUGHT.map((d) => th(d, "adaptive", "normal_volatile", "false_alarm_rate")), 1);
  N.catchVolFixed = range(UNTAUGHT.map((d) => th(d, "fixed", "spoof_volatile", "catch_rate", 16)));
  N.catchVolAdapt = range(UNTAUGHT.map((d) => th(d, "adaptive", "spoof_volatile", "catch_rate", 16)));
  N.genFixed = range(UNTAUGHT.map((d) => th(d, "fixed", "control_calm", "flag_rate", 16)));
  N.genAdapt = range(UNTAUGHT.map((d) => th(d, "adaptive", "control_calm", "flag_rate", 16)));
  N.alertsVolFixed = (() => { const v = UNTAUGHT.map((d) => th(d, "fixed", "normal_volatile", "false_alerts_per_session")).filter((x) => x !== undefined); return v.length ? `${Math.min(...v).toFixed(1)}–${Math.max(...v).toFixed(1)}` : "n/a"; })();
  const B = T.budget || [];
  const bud = (name) => B.find((r) => r.detector === name) || {};
  const SEEN = "Legal definition, as the market sees it";
  N.budSeenFa = (bud(SEEN).false_alerts_per_session_calm ?? NaN).toFixed(2);
  N.budSeenP10 = pct(bud(SEEN).precision_1_in_10);
  N.budSeenP100 = pct(bud(SEEN).precision_1_in_100);
  const untaughtB = B.filter((r) => UNTAUGHT.includes(r.detector));
  N.budUntP10 = range(untaughtB.map((r) => r.precision_1_in_10));
  N.budUntP100 = range(untaughtB.map((r) => r.precision_1_in_100));
  N.budUntFa = untaughtB.length ? `${Math.min(...untaughtB.map((r) => r.false_alerts_per_session_calm)).toFixed(1)}–${Math.max(...untaughtB.map((r) => r.false_alerts_per_session_calm)).toFixed(1)}` : "n/a";
  // Part 6: the price of a false alarm
  const F = T.frontier || [];
  const fr = (d) => F.filter((r) => r.detector === d && r.false_alarm_rate <= 0.10);
  if (F.length) {
    const seen = fr("seen"), zero = Math.min(...seen.filter((r) => r.best_payoff <= 0).map((r) => r.false_alarm_rate));
    const unw = ((T.frontier_unwatched || [])[0] || {}).unwatched_best_payoff;
    const mid = seen.filter((r) => r.best_payoff > 0 && r.best_payoff < unw - 0.01).sort((a, b) => a.false_alarm_rate - b.false_alarm_rate)[0];
    N.frZero = pct(zero, 1);
    if (mid) { N.frMid = lots(mid.best_payoff); N.frMidFa = pct(mid.false_alarm_rate, 1); }
    N.frWin = lots(Math.min(...fr("window").map((r) => r.best_payoff)));
    N.frRule = lots(Math.min(...fr("rule").map((r) => r.best_payoff)));
    N.frUnw = lots(((T.frontier_unwatched || [])[0] || {}).unwatched_best_payoff ?? NaN);
  }
  $$("[data-cnum]").forEach((n) => { if (N[n.dataset.cnum] !== undefined) n.textContent = N[n.dataset.cnum]; });

  // ---- Figure 10: what the best strategy keeps -------------------------------------------------
  function duel(box) {
    const W = 640, rowH = 46, top = 26, left = 4, labelW = 0, H = top + rowH * TARGETS.length + 34;
    const all = TARGETS.flatMap((t) => [plain(t).payoff, best(t).payoff_ci_low, best(t).payoff_ci_high]);
    const lo = Math.floor(Math.min(-0.2, ...all) * 4) / 4, hi = Math.max(0.2, ...all) * 1.08;
    const x = (v) => left + labelW + ((v - lo) / (hi - lo)) * (W - left - labelW - 12);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "For each detector, the payoff of an ordinary spoof and of the best strategy the challenger found." }, box);
    for (let v = lo; v <= hi + 1e-9; v += 0.25) {
      el("line", { x1: x(v), x2: x(v), y1: top - 8, y2: H - 30, stroke: "var(--line)", "stroke-width": v === 0 ? 1.6 : 0.8 }, svg);
      el("text", { x: x(v), y: H - 12, "text-anchor": "middle", "font-size": 11, fill: "var(--ink-3)" }, svg, v.toFixed(2));
    }
    el("text", { x: x(0) + 4, y: top - 12, "font-size": 10.5, fill: "var(--ink-3)" }, svg, "← loses   ·   gains →");
    TARGETS.forEach((t, i) => {
      const y = top + i * rowH + 22, p = plain(t), b = best(t);
      el("text", { x: left, y: y - 16, "font-size": 12.5, "font-weight": 650, fill: "var(--ink)" }, svg, NAME[t]);
      el("line", { x1: x(p.payoff), x2: x(b.payoff), y1: y, y2: y, stroke: "var(--ink-3)", "stroke-width": 1.2, "stroke-dasharray": "3 3" }, svg);
      el("line", { x1: x(b.payoff_ci_low), x2: x(b.payoff_ci_high), y1: y, y2: y, stroke: COLOUR[t], "stroke-width": 2.4, "stroke-linecap": "round" }, svg);
      el("circle", { cx: x(p.payoff), cy: y, r: 5.5, fill: "var(--paper)", stroke: COLOUR[t], "stroke-width": 2 }, svg);
      el("circle", { cx: x(b.payoff), cy: y, r: 7, fill: COLOUR[t] }, svg);
      el("text", { x: x(b.payoff), y: y - 11, "font-size": 11.5, "text-anchor": "middle", fill: "var(--ink)", "font-weight": 700 }, svg, lots(b.payoff));
    });
  }

  // ---- Figure 11: the search learning ---------------------------------------------------------------
  function learning(box) {
    const P = T.challenger_progress || [];
    const W = 640, H = 300, m = { l: 44, r: 14, t: 14, b: 36 };
    const gens = Math.max(...P.map((r) => r.generation));
    const vals = P.map((r) => r.best_search_score);
    const lo = Math.min(0, ...vals), hi = Math.max(...vals) * 1.1;
    const x = (g) => m.l + (g / gens) * (W - m.l - m.r), y = (v) => H - m.b - ((v - lo) / (hi - lo)) * (H - m.t - m.b);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "The best payoff found so far, round by round, for each detector the challenger played against." }, box);
    for (let i = 0; i <= 4; i++) {
      const v = lo + ((hi - lo) * i) / 4;
      el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: "var(--line)", "stroke-width": 0.8 }, svg);
      el("text", { x: m.l - 6, y: y(v) + 4, "text-anchor": "end", "font-size": 11, fill: "var(--ink-3)" }, svg, v.toFixed(2));
    }
    [0, 5, 10, 15, 20, 25].filter((g) => g <= gens).forEach((g) => el("text", { x: x(g), y: H - m.b + 18, "text-anchor": "middle", "font-size": 11, fill: "var(--ink-3)" }, svg, g));
    el("text", { x: (m.l + W - m.r) / 2, y: H - 4, "text-anchor": "middle", "font-size": 11, fill: "var(--ink-3)" }, svg, "Round of the search");
    const lines = {};
    const SEARCHED = TARGETS.filter((t) => P.some((r) => r.target === t));
    SEARCHED.forEach((t) => {
      const q = P.filter((r) => r.target === t).sort((a, b) => a.generation - b.generation);
      const d = q.map((r, i) => `${i ? "L" : "M"}${x(r.generation).toFixed(1)},${y(r.best_search_score).toFixed(1)}`).join("");
      lines[t] = el("path", { d, fill: "none", stroke: COLOUR[t], "stroke-width": t === "seen" ? 3 : 2, "stroke-linejoin": "round" }, svg);
      const last = q[q.length - 1];
      lines[t].dataset.end = `${x(last.generation)},${y(last.best_search_score)}`;
    });
    const legend = el("div", { class: "chart-legend" }, box.parentElement);
    SEARCHED.forEach((t) => {
      const b = el("button", { type: "button", class: "legend-item", "aria-pressed": "true" }, legend);
      el("span", { class: "legend-key", style: `background:${COLOUR[t]};height:4px;border-radius:2px` }, b);
      b.append(NAME[t]);
      b.addEventListener("click", () => {
        const on = b.getAttribute("aria-pressed") !== "true";
        b.setAttribute("aria-pressed", String(on));
        b.classList.toggle("is-dim", !on);
        lines[t].style.opacity = on ? 1 : 0.08;
      });
    });
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce && "IntersectionObserver" in window) {
      Object.values(lines).forEach((p) => { const L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L; });
      const io = new IntersectionObserver(([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        Object.values(lines).forEach((p, i) => { p.style.transition = `stroke-dashoffset 1.4s cubic-bezier(0.23,1,0.32,1) ${i * 120}ms`; p.style.strokeDashoffset = 0; });
      }, { threshold: 0.3 });
      io.observe(box);
    }
  }

  // ---- tables -------------------------------------------------------------------------------------------
  function table(container, head, body, numFrom = 1) {
    if (!container) return;
    container.innerHTML = "";
    const t = el("table", { class: "booktabs" }, container);
    const tr = el("tr", {}, el("thead", {}, t));
    head.forEach((h, i) => el("th", { scope: "col", class: i >= numFrom ? "num" : "" }, tr, h));
    const tb = el("tbody", {}, t);
    body.forEach((row) => {
      const r = el("tr", {}, tb);
      row.forEach((c, i) => el(i === 0 ? "th" : "td", i === 0 ? { scope: "row" } : { class: i >= numFrom ? "num" : "" }, r, c));
    });
  }

  $$("[data-chart='duel']").forEach(duel);
  $$("[data-chart='learning']").forEach(learning);
  table($("[data-ctable='best']"), ["Played against", "Best strategy found", "Payoff (95% CI)", "Caught: rule", "windows", "order life", "as seen", "both"],
    TARGETS.flatMap((t) => [plain(t), best(t)].map((r, j) => [`${NAME[t]}${j ? "" : " (ordinary spoof)"}`, j ? r.strategy : "16× wall, 1–2 ticks back",
      `${lots(r.payoff)} (${lots(r.payoff_ci_low)} to ${lots(r.payoff_ci_high)})`, ...DETS.map((d) => pct(r[`caught_${d}`]))])), 2);
  const CASES = ["spoof", "layered spoof", "honest large order", "honest quick cancel", "honest change of mind", "market maker working off a position"];
  table($("[data-ctable='honest']"), ["Case (16×)", "Rule", "40-step windows", "Order life", "As the market sees it", "Both together"],
    [...CASES.map((c) => [c[0].toUpperCase() + c.slice(1), ...DETS.map((d) => pct((honest(c, d, 16) || {}).value))]),
      ...["calm", "volatile"].map((r) => [`False alarms, ${r} market (40-step blocks)`, "", ...["window", "order-life", "seen", "both"].map((d) => pct((honest(`normal ${r} market`, d) || {}).value, 1))])]);
  const NAMES = { Rule: "Rule", "PCA (generic)": "PCA", "IForest (generic)": "Isolation Forest", "Seq-PCA (generic)": "Sequence PCA", "LSTM-AE (generic)": "LSTM autoencoder" };
  table($("[data-ctable='thresholds']"), ["Detector", "Threshold", "False alarms, calm", "False alarms, volatile", "Spoofs caught 16×, volatile", "Honest large flagged 16×"],
    Object.keys(NAMES).flatMap((d) => ["fixed", "adaptive"].map((mode) => [NAMES[d], mode, pct(th(d, mode, "normal_calm", "false_alarm_rate"), 1),
      pct(th(d, mode, "normal_volatile", "false_alarm_rate"), 1), pct(th(d, mode, "spoof_volatile", "catch_rate", 16)), pct(th(d, mode, "control_calm", "flag_rate", 16))])), 2);
  table($("[data-ctable='budget']"), ["Detector", "Spoofs caught 16×", "False alerts per session", "Real alerts: 1 spoof per session", "1 per 10", "1 per 100"],
    B.map((r) => [NAMES[r.detector] || r.detector, pct(r.caught_16x), r.false_alerts_per_session_calm.toFixed(2), pct(r.precision_1_in_1), pct(r.precision_1_in_10), pct(r.precision_1_in_100)]));

  // ---- Figure 12: of a desk's alerts, how many are real? ---------------------------------------------
  $$("[data-chart='budget']").forEach((box) => {
    const seg = box.parentElement.querySelector("[data-prev]");
    const rows = () => { const k = seg?.querySelector("[aria-selected='true']")?.dataset.prev || "10"; return B.map((r) => ({ name: NAMES[r.detector] || r.detector, v: r[`precision_1_in_${k}`], seen: r.detector === SEEN, both: r.detector === "Both versions together", law: r.detector.startsWith("Legal") })); };
    const draw = () => {
      box.innerHTML = "";
      rows().forEach((r) => {
        const row = el("div", { class: "lab-row" }, box);
        el("span", { class: "lab-name" }, row, r.name);
        const track = el("span", { class: "lab-track", "aria-hidden": "true" }, row);
        const bar = el("span", { class: "lab-bar", style: `background:${r.seen ? "var(--det-iforest)" : r.both ? COLOUR.both : r.law ? "var(--mark)" : "var(--ink-3)"}` }, track);
        requestAnimationFrame(() => { bar.style.width = `${Math.max(0.8, (r.v || 0) * 100)}%`; });
        el("span", { class: "lab-val" }, row, pct(r.v));
      });
    };
    seg?.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
      draw();
    }));
    draw();
  });
})();
