"""Run the whole experiment end to end:

    python run_experiments.py            (re-uses simulated data in data/ if present)
    python run_experiments.py --fresh    (re-simulates everything, about 5 minutes)

Steps:
  1. Simulate trading sessions with known random seeds.
  2. Fit every detector on NORMAL training sessions only (no spoofing anywhere).
  3. Fix each detector's alert threshold on NORMAL validation sessions (~1% of bars alert).
  4. Score held-out test sessions: normal markets, spoofed markets, layered spoofs,
     and genuine large orders of the same sizes.
  5. Analyse: catch rates, threshold-free AUC, paired significance tests, the order
     (shuffle) test, a feature ablation, and whether the spoofing actually works.
  6. Save CSVs, results/summary.md and the figures in results/figures/.
"""
import argparse
from pathlib import Path

import pandas as pd

from src import config as C
from src import plots
from src.experiment import (FULL, ablation_metrics, auc_metrics, dataset_specs, evaluate,
                            impact_rows, load_or_simulate, make_detectors, paired_metrics,
                            rate_metrics, shuffle_metrics)
from src.features import bar_features
from src.market import run_session

ROOT = Path(__file__).parent
DATA, RESULTS = ROOT / "data", ROOT / "results"
DEMO_SEED = 777


def pct(x):
    return f"{100 * x:.0f}%"


def write_summary(metrics, aucs, paired, shuffled, ablation, impact, path):
    def get(condition, detector, test, metric, m=None):
        q = metrics[(metrics.condition == condition) & (metrics.detector == detector) &
                    (metrics.test == test) & (metrics.metric == metric)]
        if m is not None:
            q = q[q.size_mult == m]
        return q.iloc[0]

    def cell(row):
        return f"{pct(row.value)} ({pct(row.ci_low)}–{pct(row.ci_high)})"

    def auc_cell(detector, test, against, m, condition="calm-trained"):
        r = aucs[(aucs.condition == condition) & (aucs.detector == detector) & (aucs.test == test) &
                 (aucs.against == against) & (aucs.size_mult == m)].iloc[0]
        return f"{r.auc:.2f} ({r.ci_low:.2f}–{r.ci_high:.2f})"

    names = [d.name for d in make_detectors()]
    L = ["# Results summary", "",
         "All numbers come from simulated markets and synthetic spoofing. They describe how the detectors "
         "behave in this controlled setting, NOT real-world surveillance performance. Brackets are 95% "
         "bootstrap confidence intervals. Every detector was trained on normal calm sessions only unless "
         "stated otherwise.", "",
         "Detectors: **Rule** (large order cancelled quickly; hand-written), **PCA** and **IForest** (one "
         "5-step bar at a time), **Seq-PCA** and **LSTM-AE** (a window of the last 8 bars, so they can "
         "see the order of events). *generic* = 18 standard order-book features; *informed* = plus 6 "
         "features chosen because we know what spoofing looks like.", "",
         "## 1. Spoofs caught vs genuine large orders flagged (calm market)", "",
         "Threshold: about 1% of normal bars alert. An episode is caught if any bar in its 8-bar window alerts.", "",
         "| Detector | Spoofs, 4× | Spoofs, 8× | Spoofs, 16× | Layered, 16× | Genuine flagged, 8× | Genuine flagged, 16× | Chance |",
         "|---|---|---|---|---|---|---|---|"]
    for n in names:
        cells = [cell(get("calm-trained", n, "spoof_calm", "catch_rate", m)) for m in (4, 8, 16)]
        cells.append(cell(get("calm-trained", n, "layer_calm", "catch_rate", 16)))
        cells += [cell(get("calm-trained", n, "control_calm", "flag_rate", m)) for m in (8, 16)]
        cells.append(pct(get("calm-trained", n, "normal_calm", "chance_catch_rate").value))
        L.append(f"| {n} | " + " | ".join(cells) + " |")

    L += ["", "## 2. Can a detector tell a spoof from an honest order of the same size? (AUC)", "",
          "AUC needs no threshold: 0.50 means the detector cannot tell the two apart; 1.00 means it "
          "separates them perfectly. 'vs normal' compares spoof episodes with ordinary 8-bar stretches.", "",
          "| Detector | Spoof vs normal, 16× | Spoof vs genuine, 8× | Spoof vs genuine, 16× | Layered vs genuine, 16× |",
          "|---|---|---|---|---|"]
    for n in names:
        L.append(f"| {n} | {auc_cell(n, 'spoof_calm', 'normal', 16)} | {auc_cell(n, 'spoof_calm', 'genuine', 8)} | "
                 f"{auc_cell(n, 'spoof_calm', 'genuine', 16)} | {auc_cell(n, 'layer_calm', 'genuine', 16)} |")

    L += ["", "## 3. The order test: do the sequence detectors use the order of events?", "",
          "Each window is scored again with its bars in a random order. If results barely change, the "
          "detector is not really using the order.", "",
          "| Detector | Test | Size | Caught (intact → shuffled) | AUC vs genuine (intact → shuffled) |",
          "|---|---|---|---|---|"]
    for (det, test, m), q in shuffled.groupby(["detector", "test", "size_mult"], sort=False):
        if m not in (8, 16):
            continue
        a, b = q[q["mode"] == "intact"].iloc[0], q[q["mode"] == "shuffled"].iloc[0]
        L.append(f"| {det} | {test.replace('_calm', '')} | {m}× | {pct(a.catch_rate)} → {pct(b.catch_rate)} | "
                 f"{a.auc_vs_genuine:.2f} → {b.auc_vs_genuine:.2f} |")

    L += ["", "## 4. Paired comparisons (same episodes, calm market)", "",
          "Difference in catch rate (A − B) with a paired bootstrap interval and two-sided p-value.", "",
          "| A | B | Test | Size | A | B | A − B (95% CI) | p |", "|---|---|---|---|---|---|---|---|"]
    for r in paired[paired.condition == "calm-trained"].itertuples():
        L.append(f"| {r.a} | {r.b} | {r.test.replace('_calm', '')} | {r.size_mult}× | {pct(r.rate_a)} | {pct(r.rate_b)} | "
                 f"{100 * r.difference:+.0f} pts ({100 * r.ci_low:+.0f} to {100 * r.ci_high:+.0f}) | {r.p_value:.3f} |")

    L += ["", "## 5. False alarms when the market regime changes", "",
          "Share of bars in NORMAL test sessions (no spoofing) that raise an alert. Target: 1%.", "",
          "| Detector | Calm → calm | Calm → volatile | Calm+volatile → calm | Calm+volatile → volatile |",
          "|---|---|---|---|---|"]
    for n in names:
        cells = [f"{100 * get(c, n, f'normal_{r}', 'false_alarm_rate').value:.1f}%"
                 for c in ("calm-trained", "mixed-trained") for r in ("calm", "volatile")]
        L.append(f"| {n} | " + " | ".join(cells) + " |")

    L += ["", "## 6. Spoofs caught in a VOLATILE market (16×), with chance levels", "",
          "| Detector | Trained calm only | (chance) | Trained calm+volatile | (chance) |", "|---|---|---|---|---|"]
    for n in names:
        cells = []
        for c in ("calm-trained", "mixed-trained"):
            cells += [cell(get(c, n, "spoof_volatile", "catch_rate", 16)),
                      pct(get(c, n, "normal_volatile", "chance_catch_rate").value)]
        L.append(f"| {n} | " + " | ".join(cells) + " |")

    L += ["", "## 7. Which spoof-informed feature does the teaching? (PCA, calm market)", "",
          "| PCA variant | Spoofs caught, 8× | Spoofs caught, 16× | Layered, 16× | Genuine flagged, 16× | AUC spoof vs genuine, 16× |",
          "|---|---|---|---|---|---|"]
    for r in ablation.itertuples():
        L.append(f"| {r.variant} | {pct(r.spoofs_caught_8)} | {pct(r.spoofs_caught_16)} | {pct(r.layered_caught_16)} | "
                 f"{pct(r.genuine_flagged_16)} | {r.auc_spoof_vs_genuine_16:.2f} |")

    L += ["", "## 8. Does the spoofing actually work? (calm market, spoof vs honest twin)", "",
          "| Spoof | Size | Price shift in spoofer's favour (ticks) | Extra chance the genuine order fills | Filled with wall | Filled without |",
          "|---|---|---|---|---|---|"]
    for r in impact.itertuples():
        L.append(f"| {r.spoof} | {r.size_mult}× | {r.shift_vs_honest:+.2f} ({r.ci_low:+.2f} to {r.ci_high:+.2f}) "
                 f"| {100 * r.fill_gain:+.0f} pts ({100 * r.fill_gain_ci_low:+.0f} to {100 * r.fill_gain_ci_high:+.0f}) "
                 f"| {pct(r.fill_rate_wall)} | {pct(r.fill_rate_honest)} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true", help="re-simulate all sessions")
    args = parser.parse_args()

    print("1. Simulating / loading sessions")
    data = load_or_simulate(dataset_specs(FULL), DATA, args.fresh)

    print("2-4. Fitting detectors on normal data, setting thresholds, scoring")
    calm = evaluate(data, ["train_calm"], ["val_calm"], "calm-trained")
    mixed = evaluate(data, ["train_calm", "train_volatile"], ["val_calm", "val_volatile"], "mixed-trained")

    print("5. Analyses")
    metrics = pd.DataFrame(rate_metrics(calm) + rate_metrics(mixed))
    aucs = pd.DataFrame(auc_metrics(calm) + auc_metrics(mixed))
    paired = pd.DataFrame(paired_metrics(calm) + paired_metrics(mixed))
    shuffled = pd.DataFrame(shuffle_metrics(data, calm))
    ablation = pd.DataFrame(ablation_metrics(data, ["train_calm"], ["val_calm"]))
    impact = impact_rows(data)
    episodes = pd.DataFrame([{**e, "condition": ev.condition} for ev in (calm, mixed) for e in ev.episodes])

    print("6. Writing results")
    (RESULTS / "figures").mkdir(parents=True, exist_ok=True)
    for name, frame in [("metrics", metrics), ("auc", aucs), ("paired", paired), ("shuffle", shuffled),
                        ("ablation", ablation), ("impact", impact), ("episodes", episodes)]:
        frame.to_csv(RESULTS / f"{name}.csv", index=False)
    write_summary(metrics, aucs, paired, shuffled, ablation, impact, RESULTS / "summary.md")

    demo = run_session(DEMO_SEED, "calm", [("spoof", 8), ("control", 8)])
    figs = RESULTS / "figures"
    plots.example_session(demo, bar_features(demo), calm.fitted, figs / "fig1_example_session.png")
    plots.caught_vs_size(metrics, figs / "fig2_caught_vs_size.png")
    plots.false_alarms(metrics, figs / "fig3_false_alarms.png")
    plots.spoof_impact(impact, figs / "fig4_spoof_impact.png")
    plots.volatile_catch(metrics, figs / "fig5_volatile_market.png")
    plots.auc_genuine(aucs, figs / "fig6_spoof_vs_genuine_auc.png")
    print((RESULTS / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
