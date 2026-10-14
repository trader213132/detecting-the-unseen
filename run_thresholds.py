"""Part 5: thresholds that follow the market, and what a surveillance desk would see.

    python run_thresholds.py             (about 10 minutes; run after run_experiments.py and run_challenger.py)

Two questions a regulator would ask.

1. ADAPTIVE THRESHOLDS. Every detector so far has one fixed alert threshold, set on calm
   trading. In a jumpy market the untaught detectors then raise far more false alarms (Part 1).
   Does a threshold that follows the market fix that? The adaptive version raises the bar in
   proportion to how busy the detector's own recent scores are:

       alert if  score > tau x max(1, recent / usual)

   where `recent` is the median of the detector's scores over the previous 60 bars (300 steps)
   of the same session, and `usual` is that median on calm validation trading. It never LOWERS
   the bar: a quiet market does not make small things suspicious. tau is set, as always, so
   that about 1% of calm validation bars alert. Hypothesis (from the project plan): adaptive
   thresholds cut false alarms in a volatile market without losing spoofs. A prediction of my
   own: they cannot fix the deeper problem, because a spoof and an honest large order of the
   same size are equally unusual whatever the threshold.

2. THE ALERT BUDGET. A desk does not see "1% of bars"; it sees alerts. Here every detector's
   alerts in normal trading are counted (alerts in neighbouring bars, or by the same account in
   neighbouring windows, are one alert) and turned into PRECISION: of all the alerts a desk
   would get, how many are real spoofs? That depends on how common spoofing is, so it is shown
   for one spoof per session, per 10 sessions and per 100 sessions.

Results: results/thresholds.csv, results/alert_budget.csv, results/thresholds.md,
         results/figures/fig10_thresholds.png
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src import accounts as A
from src.evaluate import bootstrap_ci, threshold
from src.experiment import make_detectors
from src.market import run_session

ROOT = Path(__file__).parent
RESULTS, DATA = ROOT / "results", ROOT / "data"
LOOKBACK, WARMUP = 60, 20          # bars (one bar = 5 steps)
MERGE_BARS = 8                     # alerts closer than one episode window are one alert
PREVALENCE = (1, 10, 100)          # one spoof per this many sessions


def load(name):
    return pickle.loads((DATA / f"{name}.pkl").read_bytes())


def recent_median(scores):
    """Median of the detector's own scores over the previous LOOKBACK bars (the first WARMUP bars use themselves)."""
    out = np.empty(len(scores))
    for t in range(len(scores)):
        out[t] = np.median(scores[max(0, t - LOOKBACK):t] if t >= WARMUP else scores[:WARMUP])
    return out


def alerts_from_bars(flags):
    """Count alerts: runs of alerting bars, merging runs less than one episode window apart."""
    idx = np.nonzero(flags)[0]
    return 0 if len(idx) == 0 else int(1 + np.sum(np.diff(idx) > MERGE_BARS))


def alerts_from_accounts(times, accounts, gap=40):
    """Count alerts from (time, account) pairs: the same account within `gap` steps is one alert."""
    n = 0
    for a in np.unique(accounts):
        t = np.sort(times[accounts == a])
        n += 1 + int(np.sum(np.diff(t) > gap))
    return n


def market_wide():
    """Part 1's detectors (taught nothing about spoofing), fixed vs adaptive thresholds."""
    train, val = load("train_calm"), load("val_calm")
    tests = {"normal_calm": load("normal_calm"), "normal_volatile": load("normal_volatile")}
    for m in (8, 16):
        for test in ("spoof_calm", "spoof_volatile", "control_calm"):
            tests[f"{test}_{m}"] = load(f"{test}_{m}")
    rows, budget = [], []
    for det in make_detectors(informed=False):
        print(f"  fitting {det.name}")
        det.fit([s["features"] for s in train])
        val_scores = [det.score(s["features"]) for s in val]
        usual = max(float(np.median(np.concatenate(val_scores))), 1e-9)
        scale = lambda sc: np.maximum(1.0, recent_median(sc) / usual)
        taus = {"fixed": threshold(np.concatenate(val_scores)),
                "adaptive": threshold(np.concatenate([sc / scale(sc) for sc in val_scores]))}
        for name, sessions in tests.items():
            for mode in ("fixed", "adaptive"):
                hits, fprs, alerts = [], [], []
                for s in sessions:
                    sc = det.score(s["features"])
                    flags = sc > taus[mode] * (scale(sc) if mode == "adaptive" else 1.0)
                    if name.startswith("normal"):
                        fprs.append(flags[60:].mean())            # episodes never start in the first 300 steps
                        alerts.append(alerts_from_bars(flags[60:]))
                    else:
                        hits += [bool(flags[w["first_bar"]:w["last_bar"] + 1].any()) for w in s["windows"]]
                if name.startswith("normal"):
                    for metric, v in (("false_alarm_rate", fprs), ("false_alerts_per_session", alerts)):
                        low, high = bootstrap_ci(v)
                        rows.append({"detector": det.name, "mode": mode, "test": name, "size_mult": np.nan,
                                     "metric": metric, "value": float(np.mean(v)), "ci_low": low, "ci_high": high, "n": len(v)})
                else:
                    test, m = name.rsplit("_", 1)
                    low, high = bootstrap_ci(hits)
                    rows.append({"detector": det.name, "mode": mode, "test": test, "size_mult": int(m),
                                 "metric": "flag_rate" if test.startswith("control") else "catch_rate",
                                 "value": float(np.mean(hits)), "ci_low": low, "ci_high": high, "n": len(hits)})
    return pd.DataFrame(rows)


def account_level():
    """The account detectors' false alerts per session (catch rates come from run_challenger.py)."""
    import run_challenger as R
    weights = pd.read_csv(RESULTS / "visibility.csv").weight.to_numpy()
    taus = R.thresholds(weights)
    rows = []
    for regime, base in (("calm", 3000), ("volatile", 53_000)):
        counts = {"window": [], "order-life": [], "seen": [], "both": []}
        for i in range(20):
            s = run_session(base + i, regime)
            r = A.account_rows(s, 40)
            p = A.principle_score(r["X"])
            hit = p > taus["window"]
            w_time, w_acc = r["starts"][r["win"]][hit], r["account"][hit]
            counts["window"].append(alerts_from_accounts(w_time, w_acc))
            for name, w in (("order-life", None), ("seen", weights)):
                c_time, c_acc, sc = A.lifetime_scores(s, w)
                hit = sc > taus[name]
                counts[name].append(alerts_from_accounts(c_time[hit], c_acc[hit]))
            # both versions together: an alert from either, the same account within 40 steps counted once
            counts["both"].append(alerts_from_accounts(np.r_[w_time, c_time[hit]], np.r_[w_acc, c_acc[hit]]))
        for name, v in counts.items():
            low, high = bootstrap_ci(v)
            rows.append({"detector": name, "mode": "fixed", "test": f"normal_{regime}", "size_mult": np.nan,
                         "metric": "false_alerts_per_session", "value": float(np.mean(v)), "ci_low": low, "ci_high": high, "n": 20})
    return pd.DataFrame(rows)


def alert_budget(market, accounts):
    """Precision at three levels of how common spoofing is (16x spoofs, calm market, fixed thresholds)."""
    honest = pd.read_csv(RESULTS / "challenger_honest.csv")
    names = {"window": "Legal definition, 40-step windows", "order-life": "Legal definition, each order's life",
             "seen": "Legal definition, as the market sees it", "both": "Both versions together"}
    out = []

    def add(name, catch8, catch16, genuine16, fa_calm, fa_vol):
        row = {"detector": name, "caught_8x": catch8, "caught_16x": catch16, "honest_large_flagged_16x": genuine16,
               "false_alerts_per_session_calm": fa_calm, "false_alerts_per_session_volatile": fa_vol}
        for n in PREVALENCE:
            true = catch16 / n
            row[f"precision_1_in_{n}"] = true / (true + fa_calm) if true + fa_calm > 0 else np.nan
        out.append(row)

    q = market[market["mode"] == "fixed"]
    get = lambda d, test, metric, m=None: float(q[(q.detector == d) & (q.test == test) & (q.metric == metric) &
                                                 ((q.size_mult == m) if m else q.size_mult.isna())].value.iloc[0])
    for d in q.detector.unique():
        add(d, get(d, "spoof_calm", "catch_rate", 8), get(d, "spoof_calm", "catch_rate", 16),
            get(d, "control_calm", "flag_rate", 16), get(d, "normal_calm", "false_alerts_per_session"),
            get(d, "normal_volatile", "false_alerts_per_session"))
    for d, label in names.items():
        h = lambda case, m: float(honest[(honest.case == case) & (honest.detector == d) & (honest.size_mult == m)].value.iloc[0])
        fa = lambda regime: float(accounts[(accounts.detector == d) & (accounts.test == f"normal_{regime}")].value.iloc[0])
        add(label, h("spoof", 8), h("spoof", 16), h("honest large order", 16), fa("calm"), fa("volatile"))
    return pd.DataFrame(out)


def report(market, budget):
    L = ["# Part 5: thresholds that follow the market, and the alert budget", "",
         "## Fixed vs adaptive thresholds (Part 1's detectors; trained on calm trading only)", "",
         "Both versions let about 1% of calm validation bars alert. *False alerts* are per 2,000-step session "
         "(neighbouring alerting bars count once).", "",
         "| Detector | Threshold | False alarms, calm | False alarms, volatile | False alerts/session, volatile | "
         "Spoofs caught 16x, calm | Spoofs caught 16x, volatile | Honest large orders flagged 16x |", "|---|---|---|---|---|---|---|---|"]
    for d in market.detector.unique():
        for mode in ("fixed", "adaptive"):
            q = market[(market.detector == d) & (market["mode"] == mode)]
            v = lambda test, metric, m=None: q[(q.test == test) & (q.metric == metric) &
                                               ((q.size_mult == m) if m else q.size_mult.isna())].value.iloc[0]
            L.append(f"| {d} | {mode} | {v('normal_calm', 'false_alarm_rate'):.1%} | {v('normal_volatile', 'false_alarm_rate'):.1%} | "
                     f"{v('normal_volatile', 'false_alerts_per_session'):.1f} | {v('spoof_calm', 'catch_rate', 16):.0%} | "
                     f"{v('spoof_volatile', 'catch_rate', 16):.0%} | {v('control_calm', 'flag_rate', 16):.0%} |")
    L += ["", "## The alert budget: of a desk's alerts, how many are real? (fixed thresholds, calm market)", "",
          "| Detector | Spoofs caught 16x | Honest large orders flagged 16x | False alerts/session, calm | volatile | "
          "Precision, 1 spoof per session | per 10 sessions | per 100 sessions |", "|---|---|---|---|---|---|---|---|"]
    for r in budget.itertuples():
        L.append(f"| {r.detector} | {r.caught_16x:.0%} | {r.honest_large_flagged_16x:.0%} | {r.false_alerts_per_session_calm:.2f} | "
                 f"{r.false_alerts_per_session_volatile:.2f} | {r.precision_1_in_1:.0%} | {r.precision_1_in_10:.0%} | {r.precision_1_in_100:.0%} |")
    (RESULTS / "thresholds.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    cache = DATA / "thresholds_market.pkl"           # refitting the LSTM is the slow part; --fresh redoes it
    if cache.exists() and "--fresh" not in sys.argv:
        market = pickle.loads(cache.read_bytes())
    else:
        market = market_wide()
        cache.write_bytes(pickle.dumps(market))
    if "--market-only" in sys.argv:
        sys.exit()
    accounts = account_level()
    pd.concat([market, accounts]).to_csv(RESULTS / "thresholds.csv", index=False)
    budget = alert_budget(market, accounts)
    budget.to_csv(RESULTS / "alert_budget.csv", index=False)
    report(market, budget)
    from src.plots import thresholds_figure
    thresholds_figure(market, budget, RESULTS / "figures" / "fig10_thresholds.png")
    sys.stdout.reconfigure(encoding="utf-8")
    print((RESULTS / "thresholds.md").read_text(encoding="utf-8"))
