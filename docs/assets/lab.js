/* The Research Lab: pick a market situation, see how every detector reacted.
   Every value comes from the experiments' results (window.RESULTS and window.TEACHING, written by
   build_site.py). Where a detector was not tested on a situation, the lab says so instead of guessing. */
(() => {
  const R = window.RESULTS, T = window.TEACHING || {};
  const box = document.querySelector("[data-lab]");
  if (!box || !R || !T.principle) return;
  const $ = (s, r = document) => r.querySelector(s);
  const html = (tag, attrs = {}, parent, text) => {
    const n = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    if (text !== undefined) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };
  const pct = (v) => (v === undefined || v === null || Number.isNaN(v) ? null : `${Math.round(v * 100)}%`);
  const COND = "calm-trained", SIZES = R.sizes;

  // ---- data lookups --------------------------------------------------------------
  const part1 = (det, test, m) => {
    const t = R.catch[COND][test];
    return t && t[det] ? t[det][SIZES.indexOf(m)][0] : undefined;
  };
  const honestP1 = (det, test, m) => ((T.reversal || []).find((r) => r.detector === det && r.test === test && r.size_mult === m) || {}).value;
  const acc = (det, test, metric, m, setting = "main") => (T.principle.find((r) => r.setting === setting && r.detector === det &&
    r.test === test && r.metric === metric && (m === undefined || r.size_mult === m)) || {}).value;
  const ex = (key, m) => { const r = (T.examples || []).find((x) => x.variant === "spoofs and honest large orders" && x.k === 10 && x.size_mult === m); return r && r[key] ? r[key][0] : undefined; };
  const price = (strategy, key, m) => ((T.price || []).find((r) => r.strategy === strategy && r.size_mult === m) || {})[key];
  const honestLife = (start) => ((T.price_honest || []).find((r) => r.test.startsWith(start)) || {}).value;
  const evasion = (key, test, metric, m) => ((T.evasion || []).find((r) => r.setting.includes(key) && r.test === test &&
    r.size_mult === m && r.metric === metric) || {}).value;

  // ---- the detectors, grouped by how much they were taught -----------------------------
  const P = "Principle (accounts)", U = "Untaught IForest (accounts)";
  const DETECTORS = [
    { group: "Taught nothing", name: "PCA", id: "PCA (generic)", kind: "p1" },
    { group: "Taught nothing", name: "Isolation Forest", id: "IForest (generic)", kind: "p1" },
    { group: "Taught nothing", name: "Sequence PCA", id: "Seq-PCA (generic)", kind: "p1" },
    { group: "Taught nothing", name: "LSTM neural network", id: "LSTM-AE (generic)", kind: "p1" },
    { group: "Hidden teaching", name: "PCA, spoof-informed", id: "PCA (informed)", kind: "p1" },
    { group: "Hidden teaching", name: "Isolation Forest, spoof-informed", id: "IForest (informed)", kind: "p1" },
    { group: "Taught examples", name: "Classifier, 10 spoofs + 10 honest orders", kind: "ex" },
    { group: "Taught a pattern", name: "The rule", id: "Rule", kind: "p1" },
    { group: "Taught a principle", name: "Legal definition, 40-step windows", kind: "pr" },
    { group: "Taught a principle", name: "Legal definition, each order's life", kind: "life" },
    { group: "Control", name: "Isolation Forest on account data", kind: "ua" },
  ];

  // ---- the situations -------------------------------------------------------------------
  // should: "alert" (a good detector alerts) or "quiet" (it stays silent). sized: depends on 8x / 16x.
  const SITUATIONS = [
    { id: "calm", label: "Normal market", should: "quiet", sized: false,
      text: "Ordinary trading with no spoofing at all. Every alert here is a false accusation. Values are the share of 40-step stretches that contain an alert." },
    { id: "volatile", label: "Volatile market", should: "quiet", sized: false,
      text: "Honest trading in a jumpy market the detectors never saw in training. Real volatility is not manipulation, so every alert is a false accusation." },
    { id: "spoof", label: "Spoof", should: "alert", sized: true,
      text: "A large fake wall a tick or two behind the best price, a small genuine order on the other side, and the wall cancelled as soon as the genuine order trades." },
    { id: "layer", label: "Layered spoof", should: "alert", sized: true,
      text: "The same spoof with the wall split into four smaller orders on neighbouring prices. A variant the rule was not written for." },
    { id: "control", label: "Honest large order", should: "quiet", sized: true,
      text: "A genuine order of the same size and placement as a spoof wall, left on the book until it trades or the trader loses patience." },
    { id: "withdrawal", label: "Honest quick cancel", should: "quiet", sized: true,
      text: "An honest trader places the same large order and cancels it a few steps later without trading. Exactly what the rule looks for, but innocent." },
    { id: "reversal", label: "Honest change of mind", should: "quiet", sized: true,
      text: "The same, but after cancelling the trader sells (or buys) a little the other way, as if on news. Every action matches a spoof; only the reason differs. No detector here can be right." },
    { id: "patient", label: "Patient spoofer", should: "alert", sized: true,
      text: "A spoof whose wall is left up 160 steps after the genuine order trades, so that pulling it looks unconnected. Tested on the detectors most likely to be fooled." },
    { id: "cover", label: "Spoofer who buys back", should: "alert", sized: true,
      text: "A spoof followed by buying back all it sold, so the account no longer trades only one way. It escapes, but ends worse off than an honest trader." },
    { id: "twoacc", label: "Two-account spoofer", should: "alert", sized: true,
      text: "The wall comes from one account and the genuine order from another. Shown with the regulator checking accounts one at a time." },
  ];

  function value(det, sit, m) {
    const p1 = det.kind === "p1" ? det.id : null;
    switch (sit.id) {
      case "calm":
      case "volatile": {
        if (p1) return chanceTable[`${p1}|normal_${sit.id}`];
        if (det.kind === "pr") return acc(P, `normal_${sit.id}`, "false_alarm_windows");
        if (det.kind === "ua") return acc(U, `normal_${sit.id}`, "false_alarm_windows");
        if (det.kind === "life") return honestLife(`false alarms, normal ${sit.id}`);
        return undefined;
      }
      case "spoof": case "layer": {
        const test = sit.id === "spoof" ? "spoof_calm" : "layer_calm";
        if (p1) return part1(p1, test, m);
        if (det.kind === "ex") return ex(sit.id === "spoof" ? "spoof_walls_caught" : "layered_caught", m);
        if (det.kind === "pr") return acc(P, test, "catch_rate", m);
        if (det.kind === "ua") return acc(U, test, "catch_rate", m);
        if (det.kind === "life" && sit.id === "spoof") return price("no evasion", "caught_lifetime", m);
        return undefined;
      }
      case "control": case "withdrawal": case "reversal": {
        if (p1) return sit.id === "control" ? part1(p1, "control_calm", m) : honestP1(p1, `${sit.id}_calm`, m);
        if (det.kind === "ex") return ex({ control: "genuine_flagged", withdrawal: "withdrawal_flagged", reversal: "reversal_flagged" }[sit.id], m);
        if (det.kind === "pr") return acc(P, `${sit.id}_calm`, "flag_rate", m);
        if (det.kind === "ua") return acc(U, `${sit.id}_calm`, "flag_rate", m);
        if (det.kind === "life" && m === 16) return honestLife({ control: "honest large", withdrawal: "honest quick", reversal: "honest changes" }[sit.id]);
        return undefined;
      }
      case "patient": case "cover": {
        const s = sit.id === "patient" ? "patient: 160 steps" : "buys back all 3 lots";
        if (p1 === "Rule") return price(s, "caught_rule", m);
        if (det.kind === "pr") return price(s, "caught_principle40", m);
        if (det.kind === "life") return price(s, "caught_lifetime", m);
        return undefined;
      }
      case "twoacc":
        if (det.kind === "pr") return evasion("one account at a time", "spoof_calm", "catch_rate", m);
        return undefined;
      default: return undefined;
    }
  }

  // Part 1's window-level chance rates (an alert anywhere in a 40-step stretch of normal trading),
  // written per detector by build_site.py into RESULTS.chance_by_detector.
  const chanceTable = R.chance_by_detector || {};

  // ---- the controls ---------------------------------------------------------------------
  let sit = SITUATIONS[2], size = 16;
  const pickers = $("[data-lab-situations]", box);
  SITUATIONS.forEach((s) => {
    const b = html("button", { type: "button", class: `lab-chip lab-chip--${s.should}`, "aria-pressed": String(s === sit), "data-id": s.id }, pickers, s.label);
    b.addEventListener("click", () => { sit = s; render(); });
  });
  const sizeGroup = $("[data-lab-size]", box);
  sizeGroup.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { size = Number(b.dataset.size); render(); }));

  const out = $("[data-lab-out]", box);
  function render() {
    pickers.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === sit.id)));
    sizeGroup.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.size) === size)));
    sizeGroup.hidden = !sit.sized;
    $("[data-lab-text]", box).textContent = sit.text;
    const should = $("[data-lab-should]", box);
    should.textContent = sit.should === "alert" ? "A good detector should raise an alert" : "A good detector should stay quiet";
    should.className = `lab-should lab-should--${sit.should}`;
    $("[data-lab-unit]", box).textContent = sit.should === "alert" ? "Share of these spoofs that raised an alert" :
      (sit.id === "calm" || sit.id === "volatile" ? "Share of 40-step stretches with a false alert" : "Share of these honest traders wrongly flagged");
    out.innerHTML = "";
    let group = null;
    const rows = DETECTORS.map((d) => ({ d, v: value(d, sit, sit.sized ? size : undefined) }));
    rows.forEach(({ d, v }) => {
      if (d.group !== group) { group = d.group; html("p", { class: "lab-group" }, out, group); }
      const row = html("div", { class: `lab-row${v === undefined ? " is-untested" : ""}` }, out);
      html("span", { class: "lab-name" }, row, d.name);
      const track = html("span", { class: "lab-track", "aria-hidden": "true" }, row);
      const bar = html("span", { class: `lab-bar lab-bar--${sit.should}` }, track);
      requestAnimationFrame(() => { bar.style.width = v === undefined ? "0%" : `${Math.max(0.8, v * 100)}%`; });
      html("span", { class: "lab-val" }, row, v === undefined ? "not tested" : pct(v));
    });
    const tested = rows.filter((r) => r.v !== undefined);
    const verdict = $("[data-lab-verdict]", box);
    if (sit.id === "reversal") {
      verdict.textContent = "Every detector that catches spoofs also flags this honest trader: the actions are identical, so only an investigation into the reason can tell them apart.";
    } else if (tested.length) {
      // Name every detector that ties for best and for worst.
      const vals = tested.map((r) => r.v);
      const hi = Math.max(...vals), lo = Math.min(...vals);
      const names = (v) => tested.filter((r) => pct(r.v) === pct(v)).map((r) => r.d.name);
      const list = (xs) => (xs.length > 2 ? `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}` : xs.join(" and "));
      verdict.textContent = sit.should === "alert"
        ? `Caught most: ${list(names(hi))} (${pct(hi)}). Caught fewest: ${list(names(lo))} (${pct(lo)}).`
        : `Fewest false accusations: ${list(names(lo))} (${pct(lo)}). Most: ${list(names(hi))} (${pct(hi)}). Staying quiet only counts if the same detector also catches spoofs.`;
    }
  }
  render();
})();
