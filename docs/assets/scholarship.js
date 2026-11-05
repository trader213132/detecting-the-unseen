/* Scholarship portfolio: an illustrative Bayesian calculator. Bayes' theorem gives the chance that an
   alert is genuine:  P(manipulation | alert) = s·p / (s·p + f·(1 − p)),
   where p is the prevalence, s the sensitivity (true-positive rate) and f the false-positive rate.
   Illustrative only: it is not an experimental result. */
(() => {
  "use strict";
  const box = document.querySelector("[data-bayes]");
  if (!box) return;
  const $ = (id) => document.getElementById(id);
  const prev = $("b-prev"), sens = $("b-sens"), fpr = $("b-fpr");
  const pct = (x, d = 1) => `${(x * 100).toFixed(d)}%`;
  const whole = (x) => Math.round(x).toLocaleString("en-GB");

  function posterior(p, s, f) {
    const hit = s * p, false_ = f * (1 - p);
    return hit + false_ === 0 ? 0 : hit / (hit + false_);
  }

  function update() {
    const p = Number(prev.value) / 100, s = Number(sens.value) / 100, f = Number(fpr.value) / 100;
    $("b-prev-out").textContent = pct(p);
    $("b-sens-out").textContent = pct(s, 0);
    $("b-fpr-out").textContent = pct(f);
    const post = posterior(p, s, f);
    $("b-answer").textContent = pct(post, post < 0.1 ? 1 : 0);
    // the same result as counts, out of 10,000 stretches of trading
    const N = 10000, bad = N * p, caught = bad * s, falseAlerts = (N - bad) * f;
    $("b-freq").textContent = `Out of 10,000 stretches of trading, ${whole(bad)} contain manipulation; the detector flags ${whole(caught)} of them and ${whole(falseAlerts)} honest ones.`;
    const total = caught + falseAlerts;
    $("b-bar-true").style.width = total ? `${(caught / total) * 100}%` : "0%";
    $("b-bar-false").style.width = total ? `${(falseAlerts / total) * 100}%` : "0%";
  }

  [prev, sens, fpr].forEach((el) => el.addEventListener("input", update));
  update();
})();
