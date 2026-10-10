/* Detecting the Unseen: page behaviour.
   Data: window.RESULTS, REPLAY, EXTENSIONS, TEACHING (written by build_site.py) and PROGRESS (progress.js). */
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const SVG = "http://www.w3.org/2000/svg";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const R = window.RESULTS;
  const E = window.EXTENSIONS || {};
  const T = window.TEACHING || {};
  const COND = "calm-trained";

  // Every detector keeps one look everywhere: colour = model family, shape = what it sees,
  // dashes = generic features.
  const DET = {
    "Rule": { label: "Rule", colour: "var(--det-rule)", shape: "circle", dashed: false },
    "PCA (generic)": { label: "PCA, generic", colour: "var(--det-pca)", shape: "circle", dashed: true },
    "PCA (informed)": { label: "PCA, spoof-informed", colour: "var(--det-pca)", shape: "circle", dashed: false },
    "IForest (generic)": { label: "Isolation Forest, generic", colour: "var(--det-iforest)", shape: "circle", dashed: true },
    "IForest (informed)": { label: "Isolation Forest, spoof-informed", colour: "var(--det-iforest)", shape: "circle", dashed: false },
    "Seq-PCA (generic)": { label: "Sequence PCA", colour: "var(--det-pca)", shape: "square", dashed: true },
    "LSTM-AE (generic)": { label: "LSTM autoencoder", colour: "var(--det-lstm)", shape: "square", dashed: true },
  };
  const meta = (d) => DET[d] || { label: d, colour: "var(--ink)", shape: "circle", dashed: false };

  function svg(tag, attrs = {}, parent) {
    const node = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (parent) parent.appendChild(node);
    return node;
  }
  function html(tag, attrs = {}, parent, text) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (text !== undefined) node.textContent = text;
    if (parent) parent.appendChild(node);
    return node;
  }
  // Round half to even, matching the Python summaries (12.5 -> 12).
  function roundEven(x) {
    const lower = Math.floor(x);
    if (Math.abs(x - lower - 0.5) < 1e-9) return lower % 2 === 0 ? lower : lower + 1;
    return Math.round(x);
  }
  function pct(v, digits = 0) {
    if (v === undefined || v === null || Number.isNaN(v)) return "n/a";
    return `${(roundEven(v * 100 * 10 ** digits) / 10 ** digits).toFixed(digits)}%`;
  }
  const dec = (v, d = 2) => (v === undefined || v === null ? "n/a" : Number(v).toFixed(d));
  const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  function parseDate(s) { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
  function fmtDate(s, opts = { day: "numeric", month: "long", year: "numeric" }) { return parseDate(s).toLocaleDateString("en-GB", opts); }
  function iso(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; }

  function tween(duration, onUpdate, onDone) {
    if (reduceMotion.matches || document.documentElement.dataset.motion === "paused" || duration <= 0) { onUpdate(1); if (onDone) onDone(); return () => {}; }
    let raf, start;
    const step = (now) => {
      if (document.documentElement.dataset.motion === "paused") { onUpdate(1); if (onDone) onDone(); return; }
      if (start === undefined) start = now;
      const t = Math.min(1, (now - start) / duration);
      onUpdate(easeInOut(t));
      if (t < 1) raf = requestAnimationFrame(step); else if (onDone) onDone();
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }
  function onResize(el, fn) {
    let last = el.clientWidth, raf;
    new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => { if (el.clientWidth !== last) { last = el.clientWidth; fn(); } });
    }).observe(el);
  }

  /* ---------- Data lookups ---------- */
  const SIZES = R ? R.sizes : [1, 2, 4, 8, 16];
  const iSize = (m) => SIZES.indexOf(m);
  const catchRate = (det, test, m, cond = COND) => R.catch[cond][test][det][iSize(m)][0];
  const aucOf = (det, key, m, cond = COND) => (R.auc[cond][key] && R.auc[cond][key][det] ? R.auc[cond][key][det][iSize(m)] : null);
  const ordersRow = (variant, m) => (E.orders || []).find((r) => r.variant === variant && r.size_mult === m);
  const sensRow = (market, det) => (E.sensitivity || []).find((r) => r.market === market && r.detector === det);
  const resRow = (det) => (E.resolution || []).find((r) => r.detector === det);

  function numbers() {
    const n = {};
    if (!R) return n;
    const single8 = R.impact["single wall"].find((r) => r.size === 8);
    n.fill8 = String(roundEven(single8.fill_gain[0] * 100));
    n.lstmAuc16 = dec(aucOf("LSTM-AE (generic)", "spoof_calm|genuine", 16)[0]);
    n.rule16 = pct(catchRate("Rule", "spoof_calm", 16));
    n.rule8 = pct(catchRate("Rule", "spoof_calm", 8));
    n.ruleLayer16 = pct(catchRate("Rule", "layer_calm", 16));
    n.ruleThr = String(Math.round(R.thresholds[COND].Rule));
    n.pcaInfControl16 = pct(catchRate("PCA (informed)", "control_calm", 16));
    n.chance = pct(R.chance[COND].calm);
    n.nSessions = (R.n_sessions || 0).toLocaleString("en-GB");
    n.seq16 = pct(catchRate("Seq-PCA (generic)", "spoof_calm", 16));
    n.pcaGen16 = pct(catchRate("PCA (generic)", "spoof_calm", 16));
    const p = R.paired.find((r) => r.a === "Seq-PCA (generic)" && r.b === "PCA (generic)" && r.test === "spoof_calm" && r.size_mult === 16);
    n.seqP = p ? (p.p_value < 0.001 ? "p < 0.001" : `p = ${p.p_value.toFixed(3)}`) : "";
    const abl = (v) => R.ablation.find((r) => r.variant === v);
    if (abl("all informed features")) {
      n.ablAllFlag = pct(abl("all informed features").genuine_flagged_16);
      n.ablNoMaxFlag = pct(abl("without max_add").genuine_flagged_16);
      n.ablNoMaxAuc = dec(abl("without max_add").auc_spoof_vs_genuine_16);
    }
    if (E.orders) {
      n.ordersAuc16 = dec(ordersRow("all four features", 16).auc_spoof_vs_genuine);
      n.ordersNormal16 = dec(ordersRow("all four features", 16).auc_spoof_vs_normal);
      n.ordersNoSize = dec(ordersRow("without size", 16).auc_spoof_vs_normal);
    }
    if (E.sensitivity) {
      n.sensPcaMax = pct(Math.max(...E.sensitivity.filter((r) => r.detector === "PCA (generic)").map((r) => r.spoofs_caught_16)));
      const few = sensRow("fewer book-readers", "Rule");
      n.sensFewFill = few ? String(roundEven(few.fill_gain_single_wall_16 * 100)) : "n/a";
    }
    if (E.resolution) {
      n.resLstmNormal = dec(resRow("LSTM-AE (generic)").auc_spoof_vs_normal_16);
      n.resLstmGenuine = dec(resRow("LSTM-AE (generic)").auc_spoof_vs_genuine_16);
    }
    if (T.principle) {
      const P = "Principle (accounts)", U = "Untaught IForest (accounts)";
      const tp = (det, test, metric, m) => (T.principle.find((r) => r.setting === "main" && r.detector === det && r.test === test &&
        r.metric === metric && (m === undefined || r.size_mult === m)) || {}).value;
      n.prSpoof8 = pct(tp(P, "spoof_calm", "catch_rate", 8));
      n.prSpoof16 = pct(tp(P, "spoof_calm", "catch_rate", 16));
      n.prLayer8 = pct(tp(P, "layer_calm", "catch_rate", 8));
      n.prLayer16 = pct(tp(P, "layer_calm", "catch_rate", 16));
      n.prPaid16 = pct(tp(P, "spoof_calm", "catch_rate_when_it_paid", 16));
      n.prPaid8 = pct(tp(P, "spoof_calm", "catch_rate_when_it_paid", 8));
      n.prGenuine16 = pct(tp(P, "control_calm", "flag_rate", 16));
      n.prRev16 = pct(tp(P, "reversal_calm", "flag_rate", 16));
      n.prAucRev16 = dec(tp(P, "spoof_calm", "auc_vs_reversal", 16));
      n.prAucGen16 = dec(tp(P, "spoof_calm", "auc_vs_genuine", 16));
      n.prFprCalm = pct(tp(P, "normal_calm", "false_alarm_windows"), 1);
      n.prFprVol = pct(tp(P, "normal_volatile", "false_alarm_windows"), 1);
      n.prVol16 = pct(tp(P, "spoof_volatile", "catch_rate", 16));
      n.prThr = String(Math.round((T.principle.find((r) => r.setting === "main" && r.detector === P) || {}).threshold));
      n.uaCatch16 = pct(tp(U, "spoof_calm", "catch_rate", 16));
      n.uaAucGen16 = dec(tp(U, "spoof_calm", "auc_vs_genuine", 16));
      n.uaAucNormal16 = dec(tp(U, "spoof_calm", "auc_vs_normal", 16));
      n.uaFprVol = pct(tp(U, "normal_volatile", "false_alarm_windows"), 1);
      const pr = (T.paired || []).find((r) => r.b === "Rule" && r.test === "layer_calm" && r.size_mult === 16);
      if (pr) { n.prVsRuleLayer16 = `+${Math.round(pr.difference * 100)}`; n.prVsRuleP = pr.p_value < 0.001 ? "p < 0.001" : `p = ${pr.p_value.toFixed(3)}`; }
      const ex = (variant, m) => (T.examples || []).find((r) => r.variant === variant && r.k === EXAMPLES_K && r.size_mult === m);
      if (ex("spoofs only", 16)) {
        n.exOnlyGenuine16 = pct(ex("spoofs only", 16).genuine_flagged[0]);
        n.exOnlyLayer16 = pct(ex("spoofs only", 16).layered_caught[0]);
        n.exBothWalls16 = pct(ex("spoofs and honest large orders", 16).spoof_walls_caught[0]);
        n.exBothLayer16 = pct(ex("spoofs and honest large orders", 16).layered_caught[0]);
        n.exBothLayer8 = pct(ex("spoofs and honest large orders", 8).layered_caught[0]);
        n.exBothGenuine16 = pct(ex("spoofs and honest large orders", 16).genuine_flagged[0]);
        n.exK = String(EXAMPLES_K);
      }
      const rv = (det, test = "reversal_calm") => (T.reversal || []).find((r) => r.detector === det && r.test === test && r.size_mult === 16);
      if (rv("Rule")) { n.ruleRev16 = pct(rv("Rule").value); n.lstmRev16 = pct(rv("LSTM-AE (generic)").value); }
      if (rv("Rule", "withdrawal_calm")) n.ruleWd16 = pct(rv("Rule", "withdrawal_calm").value);
      n.prWd16 = pct(tp(P, "withdrawal_calm", "flag_rate", 16));
      if (ex("spoofs and honest large orders", 16) && ex("spoofs and honest large orders", 16).withdrawal_flagged)
        n.exBothWd16 = pct(ex("spoofs and honest large orders", 16).withdrawal_flagged[0]);
      if (T.evasion) {
        const ev = (label, test, m, metric) => T.evasion.find((r) => r.setting.includes(label) && r.test === test &&
          (m === undefined || r.size_mult === m) && r.metric === metric) || {};
        n.evOne16 = pct(ev("one account at a time", "spoof_calm", 16, "catch_rate").value);
        n.evLinked16 = pct(ev("links accounts", "spoof_calm", 16, "catch_rate").value);
        n.evPairs16 = pct(ev("every pair", "spoof_calm", 16, "catch_rate").value);
        n.evPairsWd16 = pct(ev("every pair", "withdrawal_calm", 16, "flag_rate").value);
        n.evLinkedWd16 = pct(ev("links accounts", "withdrawal_calm", 16, "flag_rate").value);
        n.evOneThr = String(Math.round(ev("one account at a time", "normal_calm", undefined, "false_alarm_windows").threshold));
        n.evPairsThr = String(Math.round(ev("every pair", "normal_calm", undefined, "false_alarm_windows").threshold));
      }
      if (T.accounts) {
        const ac = (label, test, m, metric) => T.accounts.find((r) => r.setting === label && r.test === test && r.size_mult === m && r.metric === metric) || {};
        const pool = T.accounts.filter((r) => r.setting.includes("accounts per trader type") && r.test === "spoof_calm" &&
          r.size_mult === 8 && r.metric === "catch_rate").map((r) => r.value);
        if (pool.length) n.poolRange = Math.min(...pool) === Math.max(...pool) ? pct(pool[0]) : `${pct(Math.min(...pool))} to ${pct(Math.max(...pool))}`;
        const omni = "spoofer inside an omnibus account carrying 20% of all orders";
        n.omni20_8 = pct(ac(omni, "spoof_calm", 8, "catch_rate").value);
        n.omni20_16 = pct(ac(omni, "spoof_calm", 16, "catch_rate").value);
      }
    }
    return n;
  }
  function bindNumbers() {
    const n = numbers();
    $$("[data-num]").forEach((el) => { const v = n[el.dataset.num]; if (v !== undefined) el.textContent = v; });
  }

  /* ---------- Theme ---------- */
  function initTheme() {
    const btn = $("#theme-toggle");
    if (!btn) return;
    const dark = () => {
      const set = document.documentElement.dataset.theme;
      return set ? set === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    };
    btn.addEventListener("click", () => {
      const next = dark() ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("dtu-theme", next); } catch (e) { /* storage unavailable */ }
      window.dispatchEvent(new Event("themechange"));
    });
  }

  /* ---------- Segmented controls ---------- */
  function placePill(group) {
    const pill = $(".segmented__pill", group);
    const active = $('button[aria-pressed="true"], button[aria-selected="true"]', group);
    if (!pill || !active) return;
    pill.style.width = `${active.offsetWidth}px`;
    pill.style.transform = `translateX(${active.offsetLeft - 3}px)`;
  }
  function initSegmented() {
    $$(".segmented").forEach((group) => {
      const pill = $(".segmented__pill", group);
      if (pill) pill.style.transition = "none";
      placePill(group);
      requestAnimationFrame(() => requestAnimationFrame(() => { if (pill) pill.style.transition = ""; }));
      onResize(group, () => placePill(group));
      if (group.getAttribute("role") === "tablist") {
        group.addEventListener("keydown", (e) => {
          if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
          const tabs = $$("button", group);
          const i = tabs.indexOf(document.activeElement);
          if (i < 0) return;
          const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
          next.focus(); next.click(); e.preventDefault();
        });
        $$("button", group).forEach((b) => { b.tabIndex = b.getAttribute("aria-selected") === "true" ? 0 : -1; });
      }
    });
    if (document.fonts) document.fonts.ready.then(() => $$(".segmented").forEach(placePill));
  }
  function select(group, button) {
    $$("button", group).forEach((b) => {
      const on = b === button;
      if (b.hasAttribute("aria-pressed")) b.setAttribute("aria-pressed", String(on));
      if (b.hasAttribute("aria-selected")) { b.setAttribute("aria-selected", String(on)); b.tabIndex = on ? 0 : -1; }
    });
    placePill(group);
  }
  function onTabs(group, attr, fn) {
    if (!group) return;
    $$("button", group).forEach((b) => b.addEventListener("click", () => {
      if (b.getAttribute("aria-selected") === "true" || b.getAttribute("aria-pressed") === "true") return;
      select(group, b);
      fn(b.dataset[attr]);
    }));
  }

  /* ---------- Top bar, contents, margin notes ---------- */
  function initWayfinding() {
    const bar = $("[data-topbar]");
    const hero = $(".hero");
    if (bar && hero) {
      // Solid once the reader is past the top of the landscape (an observer, not a scroll listener).
      const sentinel = document.createElement("div");
      sentinel.style.cssText = "position:absolute;top:48px;left:0;width:1px;height:1px;pointer-events:none";
      sentinel.setAttribute("aria-hidden", "true");
      hero.appendChild(sentinel);
      new IntersectionObserver(([e]) => bar.classList.toggle("is-solid", !e.isIntersecting && e.boundingClientRect.top < 0))
        .observe(sentinel);
    }
    const ids = ["question", "method", "results", "robustness", "teaching", "answer", "progress", "references"];
    const sections = ids.map((id) => document.getElementById(id)).filter(Boolean);
    // The top bar has fewer links than the contents, so some sections light up their parent link.
    const topFor = { question: "question", method: "method", results: "results", robustness: "results", teaching: "results", answer: "results",
      progress: "progress", references: "progress" };
    const visible = new Map();
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => visible.set(e.target.id, e.isIntersecting));
      const current = sections.find((s) => visible.get(s.id));
      if (!current) return;
      $$(".toc a").forEach((a) => a.toggleAttribute("aria-current", a.getAttribute("href") === `#${current.id}`));
      $$('.topnav a[href^="#"], .menu__plain').forEach((a) => a.toggleAttribute("aria-current", a.getAttribute("href") === `#${topFor[current.id]}`));
      $$("[aria-current]").forEach((a) => { if (a.getAttribute("aria-current") === "") a.setAttribute("aria-current", "true"); });
    }, { rootMargin: "-30% 0px -60% 0px" });
    sections.forEach((s) => io.observe(s));
    $$(".contents-inline a").forEach((a) => a.addEventListener("click", () => a.closest("details").removeAttribute("open")));

    // Margin notes open on tap when there is no margin to put them in.
    $$(".sn-ref").forEach((btn) => btn.addEventListener("click", () => {
      const note = document.getElementById(btn.getAttribute("aria-controls"));
      if (!note || window.matchMedia("(min-width: 1081px)").matches) return;
      const open = note.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", String(open));
    }));
  }

  /* ---------- Figure 1: the replay, driven by scrolling ---------- */
  function initReplay() {
    const fig = $("#figure-1");
    const all = window.REPLAY;
    if (!fig || !all) return;
    const rowsEl = $("[data-ladder-rows]", fig);
    const caption = $("[data-caption]", fig);
    const playBtn = $("[data-play]", fig);
    const restartBtn = $("[data-restart]", fig);
    const scrub = $("[data-scrub]", fig);
    const stepEl = $("[data-step-readout]", fig);
    const timeline = $("[data-timeline]", fig);
    const kindsGroup = $("[data-replay-kinds]", fig);
    const lamps = $$("[data-lamp]", fig);
    const steps = $$(".step");

    const maxQty = Math.max(...Object.values(all).flatMap((d) => d.frames.flatMap((f) => f.rows.flatMap((r) => [r[0], r[1]]))));
    const M = Math.ceil(maxQty / 5) * 5 + 4;
    const ruleThr = R ? Math.round(R.thresholds[COND].Rule) : 17;

    let d, kind = "spoof", idx = 0, timer = null, playing = false, phaseShown = "", activeStep = "before", chase = null;
    const rows = [];
    for (let r = 0; r < all.spoof.prices.length; r++) {
      const row = html("div", { class: "lrow" }, rowsEl);
      const bid = html("div", { class: "lside lbid" }, row);
      const px = html("div", { class: "lpx" }, row);
      const ask = html("div", { class: "lside lask" }, row);
      const mk = (side) => ({
        bar: html("span", { class: "bar" }, side), wall: html("span", { class: "seg seg--wall" }, side),
        genuine: html("span", { class: "seg seg--genuine" }, side), qty: html("span", { class: "lqty" }, side) });
      rows.push({ row, px, bid: mk(bid), ask: mk(ask) });
    }

    const words = () => (d.wall_side === "bid"
      ? { wall: "buy", genuine: "sell", wallPlace: "below the best bid", genuinePlace: "at the best ask", heavy: "bid", lean: "buying" }
      : { wall: "sell", genuine: "buy", wallPlace: "above the best ask", genuinePlace: "at the best bid", heavy: "ask", lean: "selling" });
    const frameAt = (t) => Math.max(0, d.frames.findIndex((f) => f.t >= t));
    function firstAlert(det) {
      const b = d.bars.find((bar) => bar.end >= d.start && bar.end <= d.window_end && bar.scores[det] > 1);
      return b ? b.end : null;
    }
    function wallDistance() {
      const before = d.frames[frameAt(d.start) - 1] || d.frames[0];
      const at = d.frames[frameAt(d.start)];
      const touch = d.wall_side === "bid" ? before.bb : before.ba;
      const wallPrices = d.prices.filter((p, r) => at.rows[r][2] > 0);
      if (!wallPrices.length || touch == null) return null;
      return Math.abs(touch - (d.wall_side === "bid" ? Math.max(...wallPrices) : Math.min(...wallPrices)));
    }
    const targets = () => ({ before: Math.max(0, frameAt(d.start) - 3), wall: frameAt(d.start), lean: frameAt(d.start) + 3,
      pulled: frameAt(d.end), result: d.frames.length - 1 });

    function paintSide(cells, side, total, special, isWall) {
      const sign = side === "bid" ? -1 : 1;
      cells.bar.style.transform = `scaleX(${total / M})`;
      const seg = isWall ? cells.wall : cells.genuine;
      (isWall ? cells.genuine : cells.wall).style.transform = "scaleX(0)";
      seg.style.transform = special > 0 ? `translateX(${(sign * (total - special) / M) * 100}%) scaleX(${special / M})` : "scaleX(0)";
      cells.qty.textContent = total > 0 ? String(total) : "";
      cells.qty.style.setProperty("--q-pos", `${(total / M) * 100}%`);
      cells.qty.classList.toggle("is-wall", isWall && special > 0);
    }
    function render(i) {
      idx = Math.max(0, Math.min(d.frames.length - 1, i));
      const f = d.frames[idx];
      const wallOnBid = d.wall_side === "bid";
      f.rows.forEach(([bid, ask, wall, genuine], r) => {
        const cell = rows[r], price = d.prices[r];
        cell.px.textContent = String(price);
        paintSide(cell.bid, "bid", bid, wallOnBid ? wall : genuine, wallOnBid);
        paintSide(cell.ask, "ask", ask, wallOnBid ? genuine : wall, !wallOnBid);
        cell.row.classList.toggle("is-best", price === f.bb || price === f.ba);
        cell.row.classList.toggle("is-best-bid", price === f.bb);
        cell.row.classList.toggle("is-best-ask", price === f.ba);
      });
      scrub.value = String(idx);
      stepEl.textContent = `Step ${f.t}`;
      drawPlayhead();
      lamps.forEach((lamp) => {
        const at = firstAlert(lamp.dataset.lamp);
        const on = at !== null && f.t >= at;
        lamp.classList.toggle("is-alert", on);
        $(".lamp__state", lamp).textContent = on ? `alert at step ${at}` : "quiet";
      });
      updateCaption(f.t);
    }
    function updateCaption(t) {
      const w = words();
      let key, text;
      if (t < d.start) { key = "before"; text = "An ordinary moment in the simulated market. Each bar is the number of lots waiting at that price."; }
      else if (t < d.end) {
        key = "wall";
        const dist = wallDistance();
        const where = dist ? `${dist} tick${dist === 1 ? "" : "s"} ${w.wallPlace}` : w.wallPlace;
        text = d.kind === "spoof"
          ? `<strong>Step ${d.start}.</strong> A ${d.wall_size}-lot ${w.wall} order appears ${where}, with a genuine ${d.genuine_size}-lot ${w.genuine} order ${w.genuinePlace}.`
          : `<strong>Step ${d.start}.</strong> The same ${d.wall_size} lots arrive as ${d.pieces} orders of ${d.wall_size / d.pieces} lots, ${w.wallPlace}.`;
      } else if (t < d.end + 3) { key = "pulled"; text = `<strong>Step ${d.end}.</strong> The genuine order fills and the wall is cancelled in the same step.`; }
      else {
        key = "result";
        const ruleAt = firstAlert("Rule");
        text = ruleAt !== null
          ? `<strong>Result.</strong> The rule alerted at step ${ruleAt}. The learned detectors stayed quiet.`
          : `<strong>Result.</strong> Nothing alerted. Each ${d.wall_size / d.pieces}-lot piece is under the rule's ${ruleThr}-lot threshold.`;
      }
      if (key !== phaseShown) { caption.innerHTML = text; phaseShown = key; }
    }
    function stepTexts() {
      const w = words();
      const dist = wallDistance();
      const wallP = $('[data-step-text="wall"]');
      if (wallP) wallP.textContent = d.kind === "spoof"
        ? `The spoofer adds a ${d.wall_size}-lot ${w.wall} order ${dist ? `${dist} ticks ` : ""}${w.wallPlace}, and a small genuine ${w.genuine} order ${w.genuinePlace}. The large order is not meant to trade.`
        : `This time the same ${d.wall_size} lots arrive as ${d.pieces} orders of ${d.wall_size / d.pieces} lots on neighbouring prices ${w.wallPlace}, with the same small genuine order.`;
      const resP = $('[data-step-text="result"]');
      if (resP) {
        const ruleAt = firstAlert("Rule");
        resP.innerHTML = d.kind === "spoof"
          ? (ruleAt !== null
            ? `Only the hand-written rule alerted, because it was told that a large order cancelled quickly is suspicious. Now switch to <b>Layered</b>: the same lots in four smaller orders.`
            : `No detector alerted.`)
          : `Nothing alerted. Each piece is under the rule's ${ruleThr}-lot threshold, and the learned detectors saw nothing unusual. The spoof still worked.`;
      }
    }

    function drawTimeline() {
      timeline.innerHTML = "";
      const w = timeline.clientWidth || 300;
      const t0 = d.frames[0].t, t1 = d.frames[d.frames.length - 1].t;
      const x = (t) => 7 + ((t - t0) / (t1 - t0)) * (w - 14);
      timeline.setAttribute("viewBox", `0 0 ${w} 22`);
      svg("rect", { x: x(d.start), y: 4, width: Math.max(3, x(d.end) - x(d.start)), height: 14, rx: 3, fill: "var(--mark-wash)" }, timeline);
      svg("text", { x: x(d.start) + (x(d.end) - x(d.start)) / 2, y: 2, "text-anchor": "middle", "font-size": 10, fill: "var(--mark-ink)",
        "font-family": "var(--font-display)", "font-weight": 600 }, timeline).textContent = "spoof";
      const ruleAt = firstAlert("Rule");
      if (ruleAt !== null) svg("line", { x1: x(ruleAt), x2: x(ruleAt), y1: 6, y2: 18, stroke: "var(--det-rule)", "stroke-width": 2.5, "stroke-linecap": "round" }, timeline);
      svg("line", { x1: 0, x2: 0, y1: 2, y2: 20, stroke: "var(--ink)", "stroke-width": 1.5, "data-playhead": "" }, timeline);
      drawPlayhead();
    }
    function drawPlayhead() {
      const head = $("[data-playhead]", timeline);
      if (!head) return;
      const w = timeline.clientWidth || 300;
      const t0 = d.frames[0].t, t1 = d.frames[d.frames.length - 1].t;
      const xv = 7 + ((d.frames[idx].t - t0) / (t1 - t0)) * (w - 14);
      head.setAttribute("x1", xv); head.setAttribute("x2", xv);
    }

    // Move frame by frame towards a target, at a pace that makes the key moments readable.
    function goTo(target) {
      clearTimeout(chase);
      if (reduceMotion.matches || document.documentElement.dataset.motion === "paused") { render(target); return; }
      const stepOnce = () => {
        if (idx === target) return;
        render(idx + Math.sign(target - idx));
        const t = d.frames[idx].t;
        const slow = t >= d.start - 1 && t <= d.end + 1;
        chase = setTimeout(stepOnce, Math.abs(target - idx) > 12 ? 40 : slow ? 260 : 120);
      };
      stepOnce();
    }
    function setPlaying(on) {
      playing = on;
      const icon = $("i", playBtn);
      if (icon) icon.className = `ph ${on ? "ph-pause" : "ph-play"}`;
      playBtn.setAttribute("aria-label", on ? "Pause replay" : "Play replay");
      clearTimeout(timer);
      if (on) { clearTimeout(chase); tick(); }
    }
    function tick() {
      timer = setTimeout(() => {
        if (idx >= d.frames.length - 1) { setPlaying(false); return; }
        render(idx + 1);
        if (playing) tick();
      }, (() => { const t = d.frames[idx].t; return t === d.start || t === d.end ? 1400 : t > d.start - 2 && t < d.end + 3 ? 520 : 140; })());
    }
    function load(k) {
      kind = k; d = all[k]; phaseShown = "";
      scrub.max = String(d.frames.length - 1);
      drawTimeline();
      stepTexts();
      render(targets()[activeStep] ?? 0);
    }

    playBtn.addEventListener("click", () => {
      if (playing) { setPlaying(false); return; }
      if (idx >= d.frames.length - 1) render(0);
      setPlaying(true);
    });
    window.addEventListener("motionchange", (e) => {
      if (e.detail.paused) { setPlaying(false); clearTimeout(chase); }
    });
    restartBtn.addEventListener("click", () => { render(0); setPlaying(true); });
    scrub.addEventListener("input", () => { setPlaying(false); clearTimeout(chase); render(Number(scrub.value)); });
    $$("button", kindsGroup).forEach((b) => b.addEventListener("click", () => {
      if (b.dataset.kind === kind) return;
      select(kindsGroup, b);
      setPlaying(false);
      const keep = activeStep;
      load(b.dataset.kind);
      activeStep = keep;
      render(Math.max(0, targets().wall - 4));
      goTo(targets()[keep === "before" ? "result" : keep]);
    }));
    onResize(timeline, drawTimeline);

    // Each step of the story moves the replay to its moment.
    const stepIO = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        steps.forEach((s) => s.classList.toggle("is-active", s === e.target));
        activeStep = e.target.dataset.step;
        setPlaying(false);
        goTo(targets()[activeStep]);
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    steps.forEach((s) => stepIO.observe(s));
    load("spoof");
  }

  /* ---------- Chart parts ---------- */
  // On a touch screen a finger "leaves" the moment it lifts, so hiding a tooltip on leave would
  // make it flash and vanish. After a tap, tooltips stay until the next tap somewhere else.
  let lastPointer = "mouse";
  document.addEventListener("pointerdown", (e) => {
    lastPointer = e.pointerType;
    if (e.pointerType === "mouse") return;
    $$(".chart-tooltip.is-on").forEach((t) => { if (!t.parentElement.contains(e.target)) t.classList.remove("is-on"); });
  }, true);
  const HIT_R = window.matchMedia("(pointer: coarse)").matches ? 18 : 12;     // bigger targets for fingers
  function tooltipFor(container) {
    let tip = $(".chart-tooltip", container);
    if (!tip) tip = html("div", { class: "chart-tooltip", role: "status" }, container);
    return {
      show(x, y, content) {
        tip.innerHTML = content;
        tip.classList.add("is-on");
        const tw = tip.offsetWidth;
        tip.style.left = `${Math.min(Math.max(0, x - tw / 2), container.clientWidth - tw)}px`;
        tip.style.top = `${Math.max(0, y - tip.offsetHeight - 14)}px`;
      },
      hide() { if (lastPointer === "mouse") tip.classList.remove("is-on"); },
    };
  }
  function shape(kind, x, y, size, attrs, parent) {
    return kind === "square"
      ? svg("rect", { x: x - size, y: y - size, width: size * 2, height: size * 2, rx: 1.5, ...attrs }, parent)
      : svg("circle", { cx: x, cy: y, r: size, ...attrs }, parent);
  }
  function marker(det, x, y, parent, size = 4.4, cls = "pt") {
    const m = meta(det);
    return shape(m.shape, x, y, size, { class: cls, fill: m.dashed ? "var(--paper)" : m.colour, stroke: m.colour }, parent);
  }
  function legendKey(det, parent) {
    const m = meta(det);
    const s = svg("svg", { class: "legend-key", viewBox: "0 0 22 10", "aria-hidden": "true" }, parent);
    svg("line", { x1: 1, x2: 21, y1: 5, y2: 5, stroke: m.colour, "stroke-width": 2, "stroke-dasharray": m.dashed ? "4 3" : "none" }, s);
    marker(det, 11, 5, s, 3.1, "k");
    $("rect, circle", s).setAttribute("stroke-width", 1.6);
    return s;
  }
  function table(container, head, body, numericFrom = 1) {
    if (!container) return;
    container.innerHTML = "";
    const t = html("table", { class: "booktabs" }, container);
    const tr = html("tr", {}, html("thead", {}, t));
    head.forEach((h, i) => html("th", { scope: "col", class: i >= numericFrom ? "num" : "" }, tr, h));
    const tb = html("tbody", {}, t);
    body.forEach((row) => {
      const r = html("tr", {}, tb);
      row.forEach((c, i) => {
        const cell = html(i === 0 ? "th" : "td", i === 0 ? { scope: "row" } : { class: i >= numericFrom ? "num" : "" }, r);
        if (c && typeof c === "object") { cell.textContent = c.text; if (c.cls) cell.classList.add(c.cls); } else cell.textContent = c;
      });
    });
    return t;
  }
  // Lines trace themselves the first time a figure scrolls into view.
  function drawInOnView(box, redraw) {
    if (reduceMotion.matches || document.documentElement.dataset.motion === "paused") return;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      redraw();
      $$("path.line", box).forEach((p) => p.style.setProperty("--len", String(Math.ceil(p.getTotalLength()) + 2)));
      box.classList.add("is-drawing");
      setTimeout(() => box.classList.remove("is-drawing"), 1800);
    }, { threshold: 0.35 });
    io.observe(box);
  }
  function legend(container, dets, onChange) {
    if (!container) return () => null;
    let focus = null;
    dets.forEach((det) => {
      const b = html("button", { type: "button", class: "legend-item", "aria-pressed": "false" }, container);
      legendKey(det, b);
      html("span", {}, b, meta(det).label);
      b.addEventListener("click", () => {
        focus = focus === det ? null : det;
        $$(".legend-item", container).forEach((x, i) => {
          x.setAttribute("aria-pressed", String(focus === dets[i]));
          x.classList.toggle("is-dim", Boolean(focus) && focus !== dets[i]);
        });
        onChange(focus);
      });
    });
    return () => focus;
  }

  /* A line chart over the five sizes, with confidence bars, a reference line and tweened updates. */
  function sizeLineChart({ box, dets, getValues, yMax = 1, yTicks, yFmt, ref, refLabel, belowLabel, yTitle, tip }) {
    let current = null, cancel = () => {}, focus = null;
    const tooltip = tooltipFor(box);
    function draw(vals) {
      const w = box.clientWidth;
      if (w < 240) return;            // not laid out yet; the resize observer draws it later
      const h = Math.round(Math.min(400, Math.max(260, w * 0.5)));
      const m = { top: 30, right: w < 520 ? 14 : 92, bottom: 44, left: 44 };
      const x = (i) => m.left + (i / (SIZES.length - 1)) * (w - m.left - m.right);
      const y = (v) => m.top + (1 - v / yMax) * (h - m.top - m.bottom);
      box.querySelectorAll("svg").forEach((s) => s.remove());
      const s = svg("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: "img", "aria-label": `${yTitle} by order size. Data table below.` });
      box.prepend(s);
      if (belowLabel) {
        svg("rect", { x: m.left, y: y(ref), width: w - m.left - m.right, height: y(0) - y(ref), fill: "var(--paper-2)" }, s);
        svg("text", { class: "ref-label", x: m.left + 8, y: y(0) - 8 }, s).textContent = belowLabel;
      }
      svg("text", { class: "axis-label", x: 0, y: 12 }, s).textContent = yTitle;
      yTicks.forEach((v) => {
        svg("line", { class: v === 0 ? "baseline" : "gridline", x1: m.left, x2: w - m.right, y1: y(v), y2: y(v) }, s);
        svg("text", { class: "tick-label", x: m.left - 8, y: y(v) + 4, "text-anchor": "end" }, s).textContent = yFmt(v);
      });
      SIZES.forEach((sz, i) => svg("text", { class: "tick-label", x: x(i), y: h - m.bottom + 18, "text-anchor": "middle" }, s).textContent = `${sz}×`);
      svg("text", { class: "axis-label", x: m.left + (w - m.left - m.right) / 2, y: h - 6, "text-anchor": "middle" }, s).textContent = "Size of the large order";
      if (ref !== undefined) {
        svg("line", { class: "ref-line", x1: m.left, x2: w - m.right, y1: y(ref), y2: y(ref) }, s);
        if (m.right > 40) svg("text", { class: "ref-label", x: w - m.right + 6, y: y(ref) + 4 }, s).textContent = refLabel;
      }
      dets.forEach((det) => {
        if (!vals[det]) return;
        const mm = meta(det);
        const g = svg("g", { class: `series${focus && focus !== det ? " is-dim" : ""}` }, s);
        vals[det].forEach((r, i) => { if (r[1] !== undefined) svg("line", { class: "err", x1: x(i), x2: x(i), y1: y(r[1]), y2: y(r[2]), stroke: mm.colour }, g); });
        svg("path", { class: "line", d: vals[det].map((r, i) => `${i ? "L" : "M"}${x(i)},${y(r[0])}`).join(""),
          stroke: mm.colour, "stroke-dasharray": mm.dashed ? "6 4" : "none" }, g);
        vals[det].forEach((r, i) => marker(det, x(i), y(r[0]), g));
      });
      const hits = svg("g", {}, s);
      dets.forEach((det) => (vals[det] || []).forEach((r, i) => {
        const c = svg("circle", { class: "hit", cx: x(i), cy: y(r[0]), r: HIT_R }, hits);
        c.addEventListener("pointerenter", () => tooltip.show(x(i), y(r[0]), tip(det, i, r)));
        c.addEventListener("pointerleave", () => tooltip.hide());
      }));
    }
    function update(next) {
      cancel();
      if (!current) { current = next; draw(current); return; }
      const from = current;
      cancel = tween(360, (k) => {
        current = Object.fromEntries(Object.keys(next).map((det) => [det, next[det].map((r, i) =>
          r.map((v, j) => (j < 3 && from[det] && from[det][i] ? from[det][i][j] + (v - from[det][i][j]) * k : v)))]));
        draw(current);
      });
    }
    onResize(box, () => current && draw(current));
    window.addEventListener("themechange", () => current && draw(current));
    update(getValues());
    drawInOnView(box, () => draw(current));
    return { update, setFocus(f) { focus = f; draw(current); } };
  }

  /* A dot chart: one row per item, two values joined by a line. */
  function dumbbell({ box, rows, xMax, xTicks, xFmt, ref, refLabel, xTitle, labels, tip }) {
    let current = rows, cancel = () => {};
    const tooltip = tooltipFor(box);
    function draw(rs) {
      const w = box.clientWidth;
      if (w < 240) return;
      const rowH = 50;
      const m = { top: 30, right: 60, bottom: 40, left: 14 };
      const h = m.top + rowH * rs.length + m.bottom;
      const x = (v) => m.left + (v / xMax) * (w - m.left - m.right);
      box.querySelectorAll("svg").forEach((s) => s.remove());
      const s = svg("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: "img", "aria-label": `${xTitle}. Data table below.` });
      box.prepend(s);
      xTicks.forEach((v) => {
        svg("line", { class: "gridline", x1: x(v), x2: x(v), y1: m.top - 8, y2: h - m.bottom }, s);
        svg("text", { class: "tick-label", x: x(v), y: h - m.bottom + 18, "text-anchor": "middle" }, s).textContent = xFmt(v);
      });
      svg("text", { class: "axis-label", x: m.left + (w - m.left - m.right) / 2, y: h - 6, "text-anchor": "middle" }, s).textContent = xTitle;
      if (ref !== undefined) {
        svg("line", { class: "ref-line", x1: x(ref), x2: x(ref), y1: m.top - 14, y2: h - m.bottom }, s);
        svg("text", { class: "ref-label", x: x(ref) + 5, y: m.top - 16 }, s).textContent = refLabel;
      }
      rs.forEach((r, i) => {
        const y = m.top + rowH * i + rowH * 0.62;
        const mm = meta(r.det);
        svg("text", { class: "tick-label", x: m.left, y: y - 13,
          style: "fill: var(--ink-2); font-size: 12px; paint-order: stroke; stroke: var(--paper); stroke-width: 5px; stroke-linejoin: round" }, s).textContent = r.label;
        svg("line", { x1: x(r.a), x2: x(r.b), y1: y, y2: y, stroke: mm.colour, "stroke-width": 2, "stroke-opacity": 0.55 }, s);
        shape(mm.shape, x(r.a), y, 5, { class: "dot", fill: "var(--paper)", stroke: mm.colour, "stroke-width": 2 }, s);
        shape(mm.shape, x(r.b), y, 5.5, { class: "dot", fill: mm.colour, stroke: "var(--paper)", "stroke-width": 2 }, s);
        svg("text", { class: "tick-label", x: x(Math.max(r.a, r.b)) + 11, y: y + 4, style: "fill: var(--ink)" }, s).textContent = xFmt(r.b, true);
        [["a", r.a, labels[0]], ["b", r.b, labels[1]]].forEach(([k, v, lab]) => {
          const c = svg("circle", { class: "hit", cx: x(v), cy: y, r: HIT_R }, s);
          c.addEventListener("pointerenter", () => tooltip.show(x(v), y, tip(r, k, lab)));
          c.addEventListener("pointerleave", () => tooltip.hide());
        });
      });
    }
    function update(next) {
      cancel();
      const from = current;
      cancel = tween(360, (k) => {
        current = next.map((r, i) => ({ ...r, a: from[i].a + (r.a - from[i].a) * k, b: from[i].b + (r.b - from[i].b) * k }));
        draw(current);
      });
    }
    draw(current);
    onResize(box, () => draw(current));
    window.addEventListener("themechange", () => draw(current));
    return { update };
  }

  /* ---------- Figure 2: catch rates ---------- */
  function initFig2() {
    const box = $('[data-chart="fig2"]');
    if (!box || !R) return;
    const dets = R.detectors;
    const reading = $('[data-reading="fig2"]');
    let test = "spoof_calm";
    const values = (t) => Object.fromEntries(dets.map((det) => [det, R.catch[COND][t][det].map((r) => r.slice(0, 3))]));
    const chance = R.chance[COND].calm;
    const chart = sizeLineChart({
      box, dets, getValues: () => values(test), yMax: 1, yTicks: [0, 0.25, 0.5, 0.75, 1], yFmt: (v) => pct(v),
      ref: chance, refLabel: `chance ${pct(chance)}`, yTitle: "Episodes with an alert",
      tip: (det, i, r) => {
        const n = R.catch[COND][test][det][i][3];
        return `<b>${meta(det).label}</b>, ${SIZES[i]}×<br>${pct(r[0])} ${test === "control_calm" ? "flagged" : "caught"}<span class="tt-sub">95% CI ${pct(r[1])} to ${pct(r[2])}, ${n} episodes</span>`;
      },
    });
    legend($('[data-legend="fig2"]'), dets, (f) => chart.setFocus(f));
    const write = () => {
      const v = (det, m) => catchRate(det, test, m);
      if (test === "spoof_calm") {
        reading.textContent = `The rule catches ${pct(v("Rule", 8))} of spoofs from 8× upwards. No untaught detector, the LSTM included, gets past ${pct(Math.max(...["PCA (generic)", "IForest (generic)", "Seq-PCA (generic)", "LSTM-AE (generic)"].map((d) => v(d, 16))))} at 16×.`;
      } else if (test === "layer_calm") {
        reading.textContent = `Split into four smaller orders, each piece falls under the rule's ${Math.round(R.thresholds[COND].Rule)}-lot threshold: it catches ${pct(v("Rule", 16))} at 16×, and nothing else climbs far above chance.`;
      } else {
        reading.textContent = `These are honest orders, so every alert is a false alarm. PCA with spoof-informed features flags ${pct(v("PCA (informed)", 16))} of genuine 16× orders, and the LSTM ${pct(v("LSTM-AE (generic)", 16))}. The rule flags ${pct(v("Rule", 16))}.`;
      }
    };
    onTabs($("[data-fig2-tabs]"), "test", (t) => { test = t; chart.update(values(test)); write(); });
    write();
    const tests = { spoof_calm: "Single wall", layer_calm: "Layered", control_calm: "Genuine orders" };
    table($('[data-table="fig2"]'), ["Detector", "Test", ...SIZES.map((s) => `${s}×`)],
      Object.entries(tests).flatMap(([t, label]) => dets.map((det) => [meta(det).label, label, ...R.catch[COND][t][det].map((r) => pct(r[0]))])), 2);
  }

  /* ---------- Figure 3: spoof or honest order (AUC) ---------- */
  function initFig3() {
    const box = $('[data-chart="fig3"]');
    if (!box || !R) return;
    const dets = R.detectors;
    const reading = $('[data-reading="fig3"]');
    let test = "spoof_calm";
    const values = (t) => Object.fromEntries(dets.map((det) => [det, (R.auc[COND][`${t}|genuine`][det] || []).map((r) => r.slice(0, 3))]));
    const chart = sizeLineChart({
      box, dets, getValues: () => values(test), yMax: 1, yTicks: [0, 0.25, 0.5, 0.75, 1], yFmt: (v) => v.toFixed(2),
      ref: 0.5, refLabel: "no difference", belowLabel: "Honest orders look stranger", yTitle: "AUC, spoof vs genuine order",
      tip: (det, i, r) => `<b>${meta(det).label}</b>, ${SIZES[i]}×<br>AUC ${dec(r[0])}<span class="tt-sub">95% CI ${dec(r[1])} to ${dec(r[2])}</span>`,
    });
    legend($('[data-legend="fig3"]'), dets, (f) => chart.setFocus(f));
    const write = () => {
      const lstm = aucOf("LSTM-AE (generic)", `${test}|genuine`, 16)[0];
      const rule = aucOf("Rule", `${test}|genuine`, 16)[0];
      reading.textContent = test === "spoof_calm"
        ? `At 16× the rule separates them perfectly (AUC ${dec(rule)}), while the LSTM autoencoder scores ${dec(lstm)}: it finds the honest orders far stranger than the spoofs.`
        : `Layered spoofs are hidden even from the rule's threshold, yet its score still ranks them above honest orders (AUC ${dec(rule)}). A lower threshold would catch them, at the cost of more alerts: an arms race.`;
    };
    onTabs($("[data-fig3-tabs]"), "test", (t) => { test = t; chart.update(values(test)); write(); });
    write();
    table($('[data-table="fig3"]'), ["Detector", "Spoof", ...SIZES.map((s) => `${s}×`)],
      ["spoof_calm", "layer_calm"].flatMap((t) => dets.map((det) => [meta(det).label, t === "spoof_calm" ? "Single wall" : "Layered",
        ...(R.auc[COND][`${t}|genuine`][det] || []).map((r) => dec(r[0]))])), 2);
  }

  /* ---------- Figure 4: the order test ---------- */
  function initFig4() {
    const box = $('[data-chart="fig4"]');
    if (!box || !R || !R.shuffle) return;
    const get = (det, test, mode, key) => (R.shuffle.find((r) => r.detector === det && r.test === test && r.size_mult === 16 && r.mode === mode) || {})[key];
    const rows = [];
    ["Seq-PCA (generic)", "LSTM-AE (generic)"].forEach((det) => {
      [["auc_vs_normal", "vs normal trading"], ["auc_vs_genuine", "vs honest orders"]].forEach(([key, what]) => {
        rows.push({ det, label: `${meta(det).label}, ${what}`, a: get(det, "spoof_calm", "intact", key), b: get(det, "spoof_calm", "shuffled", key) });
      });
    });
    dumbbell({ box, rows, xMax: 1, xTicks: [0, 0.25, 0.5, 0.75, 1], xFmt: (v) => v.toFixed(2), ref: 0.5, refLabel: "0.5 = no difference",
      xTitle: "AUC for 16× single-wall spoofs", labels: ["real order", "shuffled"],
      tip: (r, k, lab) => `<b>${r.label}</b><br>${lab}: AUC ${dec(k === "a" ? r.a : r.b)}` });
    table($('[data-table="fig4"]'), ["Detector", "Real order", "Shuffled"], rows.map((r) => [r.label, dec(r.a), dec(r.b)]));
  }

  /* ---------- Figure 5: false alarms ---------- */
  function initFig5() {
    const box = $('[data-chart="fig5"]');
    if (!box || !R) return;
    const dets = R.detectors;
    const reading = $('[data-reading="fig5"]');
    let cond = COND;
    const rows = (c) => dets.map((det) => ({ det, label: meta(det).label, a: R.fpr[c][det].calm[0], b: R.fpr[c][det].volatile[0] }));
    const xMax = Math.ceil(Math.max(...["calm-trained", "mixed-trained"].flatMap((c) => rows(c).map((r) => Math.max(r.a, r.b)))) * 10) / 10;
    const ticks = []; for (let v = 0; v <= xMax + 1e-9; v += 0.1) ticks.push(Math.round(v * 10) / 10);
    const chart = dumbbell({ box, rows: rows(cond), xMax, xTicks: ticks, xFmt: (v, precise) => pct(v, precise ? 1 : 0), ref: 0.01, refLabel: "1% target",
      xTitle: "Normal bars raising an alert", labels: ["calm market", "volatile market"],
      tip: (r, k, lab) => `<b>${r.label}</b><br>${pct(k === "a" ? r.a : r.b, 1)} of bars alert in a ${lab}` });
    const write = () => {
      const learned = dets.filter((d) => d !== "Rule").map((d) => R.fpr[cond][d].volatile[0]);
      reading.textContent = cond === COND
        ? `Moved to a volatile market, the learned detectors flag ${pct(Math.min(...learned))} to ${pct(Math.max(...learned))} of perfectly normal bars, the sequence models worst of all. The rule stays at ${pct(R.fpr[cond].Rule.volatile[0], 1)}.`
        : `Trained on both kinds of market, false alarms fall back to ${pct(Math.min(...learned), 1)} to ${pct(Math.max(...learned), 1)}, but their catch rate on volatile-market spoofs falls with them: the earlier "detection" was mostly luck.`;
    };
    onTabs($("[data-fig5-tabs]"), "condition", (c) => { cond = c; chart.update(rows(cond)); write(); });
    write();
    table($('[data-table="fig5"]'), ["Detector", "Trained on", "Calm market", "Volatile market"],
      ["calm-trained", "mixed-trained"].flatMap((c) => rows(c).map((r) => [r.label, c === COND ? "Calm only" : "Calm + volatile", pct(r.a, 1), pct(r.b, 1)])), 2);
  }

  /* ---------- Figure 6: does the spoofing work ---------- */
  function initFig6() {
    const box = $('[data-chart="fig6"]');
    if (!box || !R) return;
    const series = { "single wall": { label: "Single-wall spoof", colour: "var(--mark)", dashed: false, shape: "circle" },
      "layered": { label: "Layered spoof", colour: "var(--mark)", dashed: true, shape: "square" } };
    Object.entries(series).forEach(([k, v]) => { DET[k] = v; });
    const vals = Object.fromEntries(Object.keys(series).map((k) => [k, R.impact[k].map((r) => r.fill_gain.slice(0, 3))]));
    const all = Object.values(vals).flat().flatMap((r) => [r[1], r[2]]);
    const lo = Math.floor(Math.min(0, ...all) * 10) / 10, hi = Math.ceil(Math.max(...all) * 10) / 10;
    const shift = (v) => v - lo;
    const shifted = Object.fromEntries(Object.entries(vals).map(([k, rows]) => [k, rows.map((r) => r.map(shift))]));
    const ticks = []; for (let v = lo; v <= hi + 1e-9; v += 0.1) ticks.push(Math.round(v * 10) / 10);
    sizeLineChart({ box, dets: Object.keys(series), getValues: () => shifted, yMax: hi - lo, yTicks: ticks.map(shift),
      yFmt: (v) => { const r = Math.round((v + lo) * 100); return `${r > 0 ? "+" : ""}${r}`; }, ref: shift(0), refLabel: "no effect",
      yTitle: "Extra fill rate (percentage points)",
      tip: (k, i) => { const r = R.impact[k][i]; return `<b>${series[k].label}, ${r.size}×</b><br>${r.fill_gain[0] >= 0 ? "+" : ""}${roundEven(r.fill_gain[0] * 100)} points<span class="tt-sub">Filled ${pct(r.fill_wall)} with the wall, ${pct(r.fill_honest)} without. ${r.n} episodes</span>`; } });
    const lg = html("div", { class: "chart-legend" }, box.parentElement);
    box.after(lg);
    Object.keys(series).forEach((k) => { const it = html("span", { class: "legend-item", style: "cursor: default" }, lg); legendKey(k, it); html("span", {}, it, series[k].label); });
    table($('[data-table="fig6"]'), ["Spoof", "Size", "Fill-rate gain", "Filled with wall", "Filled without", "Price shift (ticks)"],
      Object.keys(series).flatMap((k) => R.impact[k].map((r) => [series[k].label, `${r.size}×`, `${r.fill_gain[0] >= 0 ? "+" : ""}${roundEven(r.fill_gain[0] * 100)} pts`,
        pct(r.fill_wall), pct(r.fill_honest), `${r.shift[0] >= 0 ? "+" : ""}${r.shift[0].toFixed(2)}`])), 2);
  }

  /* ---------- Figure 8: the ladder of teaching ---------- */
  // Rows: how much a detector was told. Columns: what it caught, and which honest behaviour it flagged.
  const LADDER_TESTS = [
    { key: "spoof", label: "Spoofs caught", short: "Spoofs", want: "high" },
    { key: "layer", label: "Layered spoofs caught", short: "Layered", want: "high" },
    { key: "genuine", label: "Honest large orders flagged", short: "Honest large", want: "low" },
    { key: "withdrawal", label: "Quick withdrawals flagged", short: "Withdrawals", want: "low" },
    { key: "reversal", label: "Changes of mind flagged", short: "Changes of mind", want: "none" },
  ];
  const EXAMPLES_K = 10;
  function ladderRows(size, shown) {
    const pr = (test, metric) => (T.principle || []).find((r) => r.setting === "main" && r.detector === "Principle (accounts)" &&
      r.test === test && r.metric === metric && r.size_mult === size);
    const rev = (det, test = "reversal_calm") => (T.reversal || []).find((r) => r.detector === det && r.test === test && r.size_mult === size);
    const ex = (T.examples || []).find((r) => r.variant === shown && r.k === EXAMPLES_K && r.size_mult === size);
    const fromR = (det, test) => { const r = R.catch[COND][test][det][iSize(size)]; return [r[0], r[1], r[2]]; };
    const ci = (r) => (r ? [r.value, r.ci_low, r.ci_high] : null);
    return [
      { rung: "0", name: "Nothing", who: "LSTM autoencoder: learns what normal trading looks like",
        cells: [fromR("LSTM-AE (generic)", "spoof_calm"), fromR("LSTM-AE (generic)", "layer_calm"),
          fromR("LSTM-AE (generic)", "control_calm"), ci(rev("LSTM-AE (generic)", "withdrawal_calm")), ci(rev("LSTM-AE (generic)"))] },
      { rung: "1", name: "Examples", who: shown === "spoofs only" ? `A classifier shown ${EXAMPLES_K} labelled spoofs`
          : `A classifier shown ${EXAMPLES_K} labelled spoofs and ${EXAMPLES_K} honest large orders`,
        cells: ex ? [ex.spoof_walls_caught, ex.layered_caught, ex.genuine_flagged, ex.withdrawal_flagged || null, ex.reversal_flagged]
          : [null, null, null, null, null],
        range: true },
      { rung: "2", name: "A pattern", who: "The rule: a large order cancelled quickly",
        cells: [fromR("Rule", "spoof_calm"), fromR("Rule", "layer_calm"), fromR("Rule", "control_calm"),
          ci(rev("Rule", "withdrawal_calm")), ci(rev("Rule"))] },
      { rung: "3", name: "A principle", who: "The legal definition, checked account by account",
        cells: [ci(pr("spoof_calm", "catch_rate")), ci(pr("layer_calm", "catch_rate")),
          ci(pr("control_calm", "flag_rate")), ci(pr("withdrawal_calm", "flag_rate")), ci(pr("reversal_calm", "flag_rate"))] },
    ];
  }
  function initFig8() {
    const box = $('[data-chart="fig8"]');
    if (!box || !R || !T.principle) return;
    let size = 16, shown = "spoofs and honest large orders", cancel = () => {};
    let current = ladderRows(size, shown);
    const tooltip = tooltipFor(box);
    const colour = (t) => (t.want === "high" ? "var(--mark)" : t.want === "low" ? "var(--ink-2)" : "var(--ink-3)");
    function draw(rows) {
      const w = box.clientWidth;
      if (w < 240) return;
      const wide = w >= 680;
      const n = LADDER_TESTS.length;
      const labelW = wide ? Math.min(220, w * 0.24) : 0;
      const colGap = wide ? 14 : 0, headH = wide ? 50 : 0;
      const rowH = wide ? 74 : n * 30 + 44;
      const h = headH + rowH * rows.length + 4;
      const colW = wide ? (w - labelW - colGap * (n - 1)) / n : w - 104;
      box.querySelectorAll("svg").forEach((s) => s.remove());
      const s = svg("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: "img",
        "aria-label": "Grid: for each level of teaching, the share of spoofs and layered spoofs caught and of honest behaviour flagged. Data table below." });
      box.prepend(s);
      if (wide) LADDER_TESTS.forEach((t, j) => {
        const x0 = labelW + j * (colW + colGap);
        const head = svg("text", { class: "tick-label", x: x0, y: 12, style: "fill: var(--ink); font-size: 12px; font-weight: 600" }, s);
        head.textContent = t.label;
        const lines = wrapSvgText(head, colW - 6, 14);
        svg("text", { class: "tick-label", x: x0, y: 12 + 14 * lines }, s).textContent =
          t.want === "high" ? "higher is better" : t.want === "low" ? "lower is better" : "honest, looks like a spoof";
      });
      rows.forEach((row, i) => {
        const y0 = headH + rowH * i;
        if (i > 0) svg("line", { class: "gridline", x1: 0, x2: w, y1: y0, y2: y0 }, s);
        const title = svg("text", { x: 0, y: y0 + 22, style: "fill: var(--ink); font-size: 14px; font-weight: 700" }, s);
        title.textContent = `${row.rung}  ${row.name}`;
        const sub = svg("text", { class: "tick-label", x: 0, y: y0 + 40 }, s);
        sub.textContent = row.who;
        if (wide) wrapSvgText(sub, labelW - 14, 13);
        LADDER_TESTS.forEach((t, j) => {
          const v = row.cells[j];
          const x0 = wide ? labelW + j * (colW + colGap) : 104;
          const by = wide ? y0 + 22 : y0 + 52 + j * 30;
          if (!wide) svg("text", { class: "tick-label", x: 0, y: by + 11 }, s).textContent = t.short;
          const bw = colW - 40;
          svg("rect", { x: x0, y: by, width: bw, height: 14, rx: 3, fill: "var(--paper-2)" }, s);
          if (!v) { svg("text", { class: "tick-label", x: x0 + 4, y: by + 11 }, s).textContent = "not run"; return; }
          svg("rect", { x: x0, y: by, width: Math.max(1.5, bw * v[0]), height: 14, rx: 3, fill: colour(t) }, s);
          svg("line", { x1: x0 + bw * v[1], x2: x0 + bw * v[2], y1: by + 7, y2: by + 7, stroke: "var(--ink)", "stroke-width": 1.2, opacity: 0.55 }, s);
          svg("text", { class: "tick-label", x: x0 + bw + 6, y: by + 11, style: "fill: var(--ink); font-weight: 600" }, s).textContent = pct(v[0]);
          const hit = svg("rect", { class: "hit", x: x0, y: by - 6, width: colW, height: 26 }, s);
          const range = row.range ? "middle 80% of 30 random sets of examples" : "95% confidence interval";
          hit.addEventListener("pointerenter", () => tooltip.show(x0 + bw * v[0], by,
            `<b>${row.name}</b>, ${size}×<br>${t.label}: ${pct(v[0])}<span class="tt-sub">${pct(v[1])} to ${pct(v[2])} (${range})</span>`));
          hit.addEventListener("pointerleave", () => tooltip.hide());
        });
      });
    }
    function update() {
      const from = current, to = ladderRows(size, shown);
      cancel();
      cancel = tween(380, (k) => {
        current = to.map((row, i) => ({ ...row, cells: row.cells.map((c, j) => {
          const f = from[i].cells[j];
          return c && f ? c.map((x, q) => f[q] + (x - f[q]) * k) : c;
        }) }));
        draw(current);
      });
    }
    draw(current);
    onResize(box, () => draw(current));
    window.addEventListener("themechange", () => draw(current));
    onTabs($("[data-fig8-size]"), "size", (v) => { size = Number(v); update(); });
    onTabs($("[data-fig8-shown]"), "shown", (v) => { shown = v; update(); });
    const tableRows = [];
    [8, 16].forEach((m) => ["spoofs only", "spoofs and honest large orders"].forEach((sh) => ladderRows(m, sh).forEach((row) => {
      if (row.rung !== "1" && sh === "spoofs only") return;
      const name = row.rung === "1" ? `${row.name} (${sh === "spoofs only" ? "spoofs only" : "spoofs + honest"})` : row.name;
      tableRows.push([name, `${m}×`, ...row.cells.map((c) => (c ? pct(c[0]) : "n/a"))]);
    })));
    table($('[data-table="fig8"]'), ["Teaching", "Size", ...LADDER_TESTS.map((t) => t.label)], tableRows, 1);
  }
  // Breaks an SVG text into lines of at most maxWidth pixels. Returns the number of lines.
  function wrapSvgText(node, maxWidth, lineHeight) {
    const words = node.textContent.split(" ");
    const x = node.getAttribute("x");
    node.textContent = "";
    let line = [], tspan = svg("tspan", { x, dy: 0 }, node);
    words.forEach((word) => {
      line.push(word);
      tspan.textContent = line.join(" ");
      if (tspan.getComputedTextLength() > maxWidth && line.length > 1) {
        line.pop();
        tspan.textContent = line.join(" ");
        line = [word];
        tspan = svg("tspan", { x, dy: lineHeight }, node);
        tspan.textContent = word;
      }
    });
    return node.childNodes.length;
  }

  /* ---------- Summary page: every detector, side by side ---------- */
  function initScoreboard() {
    const box = $("[data-scoreboard]");
    if (!box || !R || !T.principle) return;
    const m = 16, i = iSize(m);
    const part1 = (det) => {
      const caught = (test) => R.catch[COND][test][det][i][0];
      const honest = (test) => ((T.reversal || []).find((r) => r.detector === det && r.test === test && r.size_mult === m) || {}).value;
      return [caught("spoof_calm"), caught("layer_calm"), caught("control_calm"), honest("withdrawal_calm"), honest("reversal_calm")];
    };
    const accounts = (det) => {
      const v = (test, metric) => (T.principle.find((r) => r.setting === "main" && r.detector === det && r.test === test &&
        r.metric === metric && r.size_mult === m) || {}).value;
      return [v("spoof_calm", "catch_rate"), v("layer_calm", "catch_rate"), v("control_calm", "flag_rate"),
        v("withdrawal_calm", "flag_rate"), v("reversal_calm", "flag_rate")];
    };
    const ex = (T.examples || []).find((r) => r.variant === "spoofs and honest large orders" && r.k === EXAMPLES_K && r.size_mult === m);
    const groups = [
      ["Taught nothing: learns what normal trading looks like", [
        ["PCA", part1("PCA (generic)")], ["Isolation Forest", part1("IForest (generic)")],
        ["Sequence PCA", part1("Seq-PCA (generic)")], ["LSTM neural network", part1("LSTM-AE (generic)")]]],
      ["Hidden teaching: features chosen with spoofing in mind", [
        ["PCA, spoof-informed", part1("PCA (informed)")], ["Isolation Forest, spoof-informed", part1("IForest (informed)")]]],
      ["Taught examples", [[`Classifier shown ${EXAMPLES_K} spoofs and ${EXAMPLES_K} honest orders`,
        ex ? ["spoof_walls_caught", "layered_caught", "genuine_flagged", "withdrawal_flagged", "reversal_flagged"].map((k) => (ex[k] || [])[0]) : []]]],
      ["Taught a pattern", [["The rule: a large order cancelled quickly", part1("Rule")]]],
      ["Taught a principle", [["The legal definition, checked per account", accounts("Principle (accounts)"), true]]],
      ["Control: the same account data, taught nothing", [["Isolation Forest on accounts", accounts("Untaught IForest (accounts)")]]],
    ];
    const cols = [["Spoofs caught", "catch"], ["Layered spoofs caught", "catch"], ["Honest large orders flagged", "flag"],
      ["Quick withdrawals flagged", "flag"], ["Changes of mind flagged", "flag"]];
    const t = html("table", { class: "scoreboard" }, box);
    html("caption", { class: "visually-hidden" }, t, "Every detector at 16 times a typical order size: share of spoofs caught and of honest behaviour flagged.");
    const hr = html("tr", {}, html("thead", {}, t));
    html("th", { scope: "col" }, hr, "Detector");
    cols.forEach(([label]) => html("th", { scope: "col" }, hr, label));
    groups.forEach(([name, rows]) => {
      const tb = html("tbody", {}, t);
      html("th", { scope: "colgroup", colspan: String(cols.length + 1) }, html("tr", { class: "scoreboard__group" }, tb), name);
      rows.forEach(([label, values, highlight]) => {
        const tr = html("tr", highlight ? { class: "is-highlight" } : {}, tb);
        html("th", { scope: "row" }, tr, label);
        cols.forEach(([col, kind], j) => {
          const v = values[j];
          const td = html("td", { "data-label": col }, tr);
          const meter = html("span", { class: `meter meter--${kind}`, "aria-hidden": "true" }, td);
          html("i", { style: `--w: ${v === undefined ? 0 : Math.max(1.5, v * 100)}%` }, meter);
          html("span", { class: "meter__v" }, td, v === undefined ? "n/a" : pct(v));
        });
      });
    });
    // The bars grow when the table first scrolls into view.
    if (reduceMotion.matches) { t.classList.add("is-in"); return; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { t.classList.add("is-in"); io.disconnect(); } }, { threshold: 0.2 });
    io.observe(t);
  }

  /* ---------- Figure 7: order-level flags ---------- */
  function initFig7() {
    const box = $('[data-chart="fig7"]');
    if (!box || !E.orders) return;
    let size = 16;
    const cats = [["genuine_flagged", "Honest large orders", "var(--ink-2)"], ["spoof_walls_flagged", "Spoof walls", "var(--mark)"],
      ["layered_flagged", "Layered spoofs", "var(--mark)"], ["normal_orders_flagged", "Ordinary orders", "var(--ask)"]];
    const values = () => { const r = ordersRow("all four features", size); return cats.map(([k]) => r[k]); };
    let current = values(), cancel = () => {};
    const tooltip = tooltipFor(box);
    function draw(vals) {
      const w = box.clientWidth;
      if (w < 240) return;
      const rowH = 46, m = { top: 6, right: 56, bottom: 36, left: w < 520 ? 120 : 170 };
      const h = m.top + rowH * cats.length + m.bottom;
      const x = (v) => m.left + v * (w - m.left - m.right);
      box.querySelectorAll("svg").forEach((s) => s.remove());
      const s = svg("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: "img", "aria-label": "Bar chart of the share of each kind of order flagged. Data table below." });
      box.prepend(s);
      [0, 0.25, 0.5, 0.75, 1].forEach((v) => {
        svg("line", { class: v === 0 ? "baseline" : "gridline", x1: x(v), x2: x(v), y1: m.top, y2: h - m.bottom }, s);
        svg("text", { class: "tick-label", x: x(v), y: h - m.bottom + 18, "text-anchor": "middle" }, s).textContent = pct(v);
      });
      cats.forEach(([k, label, colour], i) => {
        const y = m.top + rowH * i + 10;
        svg("text", { class: "tick-label", x: m.left - 10, y: y + 17, "text-anchor": "end", style: "fill: var(--ink); font-size: 12.5px" }, s).textContent = label;
        svg("rect", { x: x(0), y, width: Math.max(1.5, x(vals[i]) - x(0)), height: 24, rx: 3, fill: colour }, s);
        svg("text", { class: "tick-label", x: x(vals[i]) + 8, y: y + 17, style: "fill: var(--ink)" }, s).textContent = pct(vals[i], vals[i] < 0.01 && vals[i] > 0 ? 2 : 0);
        const hit = svg("rect", { class: "hit", x: m.left, y, width: w - m.left - m.right, height: 24 }, s);
        hit.addEventListener("pointerenter", () => tooltip.show(x(vals[i]), y, `<b>${label}</b>, ${size}×<br>${pct(vals[i], 2)} flagged`));
        hit.addEventListener("pointerleave", () => tooltip.hide());
      });
    }
    draw(current);
    onResize(box, () => draw(current));
    window.addEventListener("themechange", () => draw(current));
    onTabs($("[data-fig7-tabs]"), "size", (v) => {
      size = Number(v);
      const from = current, to = values();
      cancel();
      cancel = tween(360, (k) => { current = to.map((t, i) => from[i] + (t - from[i]) * k); draw(current); });
    });
    table($('[data-table="fig7"]'), ["Feature set", "Size", "Honest large", "Spoof walls", "Layered", "Ordinary orders", "AUC spoof vs honest"],
      E.orders.map((r) => [r.variant, `${r.size_mult}×`, pct(r.genuine_flagged), pct(r.spoof_walls_flagged), pct(r.layered_flagged),
        pct(r.normal_orders_flagged, 2), dec(r.auc_spoof_vs_genuine)]), 1);
  }

  /* ---------- Tables: ablation and robustness ---------- */
  function initTables() {
    if (R && R.ablation) {
      const t = table($('[data-table="ablation"]'), ["PCA variant", "Spoofs caught, 16×", "Genuine flagged, 16×", "AUC spoof vs genuine, 16×"],
        R.ablation.map((r) => [r.variant.replace("max_add", "largest order").replace("max_fast_cancel", "largest quick cancel")
          .replace("big_add_distance", "distance of largest order").replace("imbalance_change", "change in imbalance")
          .replace("signed_flow", "signed trade flow"), pct(r.spoofs_caught_16), pct(r.genuine_flagged_16), dec(r.auc_spoof_vs_genuine_16)]));
      if (t) { const cap = document.createElement("caption"); cap.innerHTML = "<b>Table 3.</b> PCA with spoof-informed features, refitted without one feature at a time."; t.prepend(cap); }
    }
    if (E.checks) {
      const markets = E.markets;
      const t = table($('[data-table="sensitivity"]'), ["Claim", ...markets.map((m) => m.replace("main experiment", "Main"))],
        E.checks.map((r) => [r.claim, ...markets.map((m) => ({ text: r[m] === "holds" ? "Holds" : r[m] === "fails" ? "Fails" : "n/a", cls: r[m] === "fails" ? "fails" : "" }))]), 1);
      if (t) { const cap = document.createElement("caption"); cap.innerHTML = "<b>Table 4.</b> Each claim checked in the main market and four alternatives. The claim marked as added afterwards was written after seeing the results."; t.prepend(cap); }
    }
    if (T.principle && (T.markets || T.accounts)) {
      // Table 5: the principle detector under every stress test, one row per setting.
      const P = "Principle (accounts)";
      const rows = [];
      const add = (records, setting, label) => {
        const v = (test, m, metric) => (records.find((r) => r.setting === setting && r.detector === P && r.test === test &&
          (m === undefined || r.size_mult === m) && (metric === undefined || r.metric === metric)) || {}).value;
        rows.push([label, pct(v("spoof_calm", 8, "catch_rate")), pct(v("spoof_calm", 16, "catch_rate")), pct(v("layer_calm", 16, "catch_rate")),
          pct(v("control_calm", 16, "flag_rate")), pct(v("withdrawal_calm", 16, "flag_rate")), pct(v("reversal_calm", 16, "flag_rate")),
          pct(v("normal_calm", undefined, "false_alarm_windows"), 1)]);
      };
      add(T.principle, "main", "Main market");
      const settings = (records) => [...new Set((records || []).map((r) => r.setting))];
      settings(T.markets).forEach((m) => add(T.markets, m, `Market: ${m}`));
      settings(T.accounts).forEach((m) => add(T.accounts, m, m.charAt(0).toUpperCase() + m.slice(1)));
      const t = table($('[data-table="stress"]'), ["Setting", "Spoofs, 8×", "Spoofs, 16×", "Layered, 16×", "Honest large flagged, 16×",
        "Quick withdrawals flagged, 16×", "Changes of mind flagged, 16×", "False-alarm windows"], rows, 1);
      if (t) { const cap = document.createElement("caption"); cap.innerHTML = "<b>Table 5.</b> The principle detector under every stress test. Each setting sets its own threshold on its own normal trading."; t.prepend(cap); }
    }
    if (T.evasion) {
      // Table 6: a spoofer who splits the trick across two accounts.
      const rows = [...new Set(T.evasion.map((r) => r.setting))].map((setting) => {
        const v = (test, m, metric) => (T.evasion.find((r) => r.setting === setting && r.test === test &&
          (m === undefined || r.size_mult === m) && r.metric === metric) || {});
        const label = setting.replace("two accounts; ", "");
        return [label.charAt(0).toUpperCase() + label.slice(1), pct(v("spoof_calm", 8, "catch_rate").value), pct(v("spoof_calm", 16, "catch_rate").value),
          pct(v("layer_calm", 16, "catch_rate").value), pct(v("control_calm", 16, "flag_rate").value),
          pct(v("withdrawal_calm", 16, "flag_rate").value), `${Math.round(v("normal_calm", undefined, "false_alarm_windows").threshold)} lots`];
      });
      const t = table($('[data-table="evasion"]'), ["Detector", "Spoofs, 8×", "Spoofs, 16×", "Layered, 16×", "Honest large flagged, 16×",
        "Quick withdrawals flagged, 16×", "Alert threshold"], rows, 1);
      if (t) { const cap = document.createElement("caption"); cap.innerHTML = "<b>Table 6.</b> A spoofer who shows the wall from one account and trades from another. Every version keeps false alarms to 1% of normal windows, so a higher threshold is the price of a wider search."; t.prepend(cap); }
    }
  }

  /* ---------- Progress ---------- */
  function initProgress() {
    const P = window.PROGRESS;
    if (!P) return;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const deadline = parseDate(P.deadline.date);
    const days = Math.round((deadline - today) / 86400000);
    const line = $("[data-status-line]");
    if (line) {
      const when = fmtDate(P.deadline.date, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
      line.innerHTML = days > 0 ? `<b>${days} day${days === 1 ? "" : "s"}</b> until the ${P.deadline.label}, ${when}. Last updated ${fmtDate(P.updated)}.`
        : days === 0 ? `The ${P.deadline.label} is <b>today</b>, ${when}.` : `The ${P.deadline.label} was due ${when}.`;
    }
    const up = $("#updated-date");
    if (up) { up.textContent = fmtDate(P.updated); up.setAttribute("datetime", P.updated); }

    const sched = $("[data-schedule]");
    if (sched) {
      const from = parseDate(P.schedule.from), to = parseDate(P.schedule.to), span = to - from;
      const frac = (s) => Math.min(1, Math.max(0, (parseDate(s) - from) / span));
      const axis = html("div", { class: "schedule__axis", "aria-hidden": "true" }, sched);
      html("span", {}, axis);
      const dates = html("div", { class: "schedule__dates" }, axis);
      const ticks = [];
      for (let t = new Date(from); t <= to; t.setDate(t.getDate() + 7)) ticks.push(iso(t));
      const endIso = P.schedule.to;
      const near = (a, b) => Math.abs(parseDate(a) - parseDate(b)) < 3.5 * 86400000;
      const marks = ticks.filter((t, i) => i === 0 || !near(t, endIso));
      marks.push(endIso);
      marks.forEach((t, i) => html("span", { class: i === 0 ? "is-first" : i === marks.length - 1 ? "is-last" : "", style: `left:${frac(t) * 100}%` },
        dates, fmtDate(t, { day: "numeric", month: "short" })));
      html("span", {}, axis);
      const rowsWrap = html("div", { class: "schedule__rows", role: "list" }, sched);
      const statusText = { done: "Done", now: "In progress", next: "Next" };
      P.milestones.forEach((ms) => {
        const row = html("div", { class: "schedule__row", "data-status": ms.status, role: "listitem" }, rowsWrap);
        html("span", { class: "schedule__label" }, row, ms.label);
        const track = html("div", { class: "schedule__track", "aria-hidden": "true" }, row);
        const a = frac(ms.from), b = frac(ms.to);
        html("span", { class: "schedule__span", style: `left:${a * 100}%; width:${Math.max(0.8, (b - a) * 100)}%` }, track);
        if (ms.doneOn) html("span", { class: "schedule__done", style: `left:${frac(ms.doneOn) * 100}%` }, track);
        html("span", { class: "schedule__status" }, row,
          ms.status === "done" && ms.doneOn ? `Done ${fmtDate(ms.doneOn, { day: "numeric", month: "short" })}` : statusText[ms.status] || ms.status);
        html("span", { class: "visually-hidden" }, row, `, planned ${fmtDate(ms.from, { day: "numeric", month: "short" })} to ${fmtDate(ms.to, { day: "numeric", month: "short" })}`);
      });
      if (today > from && today <= to) {
        const marker = html("div", { class: "schedule__today", "aria-hidden": "true" }, rowsWrap);
        marker.style.left = `calc(15rem + 1rem + (100% - 15rem - 6rem - 2rem) * ${(today - from) / span})`;
      }
    }
    const log = $("[data-log]");
    if (log) P.log.forEach((entry) => {
      const li = html("li", {}, log);
      html("time", { datetime: entry.date }, li, fmtDate(entry.date, { day: "numeric", month: "short", year: "numeric" }));
      const body = html("div", {}, li);
      html("h4", {}, body, entry.title);
      html("p", {}, body, entry.text);
    });
    const plan = $("[data-plan]");
    if (plan) P.plan.forEach((p) => { const div = html("div", {}, plan); html("dt", {}, div, p.when); html("dd", {}, div, p.what); });
  }

  function initFooter() {
    const g = $("[data-generated]");
    if (g && R) { g.textContent = fmtDate(R.generated); g.setAttribute("datetime", R.generated); }
  }

  initTheme();
  initSegmented();
  initWayfinding();
  bindNumbers();
  initReplay();
  initFig2();
  initFig3();
  initFig4();
  initFig5();
  initFig6();
  initFig7();
  initFig8();
  initScoreboard();
  initTables();
  initProgress();
  initFooter();
})();
