"""Two follow-up experiments that test the main results:

    python run_extensions.py               (both, about 15 minutes)
    python run_extensions.py --only sensitivity
    python run_extensions.py --only resolution

SENSITIVITY: are the conclusions an artefact of one particular simulated market?
  The core experiment is repeated (with fewer sessions) in four different markets,
  and each headline claim is checked in every one of them.

RESOLUTION: the sequence detectors could not use the order of events. Is that
  because a spoof (about 6-10 steps long) happens inside one or two 5-step bars?
  Here the features are computed every single step, and the sequence detectors
  read the last 24 steps.

Results: results/sensitivity.csv, results/resolution.csv, results/extensions.md
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.experiment import (auc_metrics, dataset_specs, evaluate, impact_rows, load_or_simulate,
                            make_detectors, rate_metrics, shuffle_metrics)

ROOT = Path(__file__).parent
DATA, RESULTS = ROOT / "data", ROOT / "results"
SMALL = {"train": 20, "val": 8, "normal": 12, "spoof": 25, "layer": 20, "control": 12}
SIZES = (8, 16)
UNTAUGHT = ["PCA (generic)", "IForest (generic)", "Seq-PCA (generic)", "LSTM-AE (generic)"]

MARKETS = {
    "fewer book-readers": {"reactive_share": 0.25, "mm_react_shift": 1.5},
    "more book-readers": {"reactive_share": 0.75, "mm_react_shift": 4.5},
    "thinner book": {"arrival_rate": 1.0, "mm_size": 2},
    "impatient traders": {"mean_patience": 20.0},
}


def key_numbers(ev, impact):
    m = pd.DataFrame(rate_metrics(ev))
    a = pd.DataFrame(auc_metrics(ev, sizes=SIZES))
    rows = []
    for det, _ in ev.fitted:
        def rate(test, size):
            q = m[(m.detector == det.name) & (m.test == test) & (m.size_mult == size)]
            return float(q.value.iloc[0]) if len(q) else np.nan

        def area(test, against, size):
            q = a[(a.detector == det.name) & (a.test == test) & (a.against == against) & (a.size_mult == size)]
            return float(q.auc.iloc[0]) if len(q) else np.nan

        fpr = m[(m.detector == det.name) & (m.test == "normal_calm") & (m.metric == "false_alarm_rate")]
        chance = m[(m.detector == det.name) & (m.test == "normal_calm") & (m.metric == "chance_catch_rate")]
        rows.append({"detector": det.name,
                     "spoofs_caught_8": rate("spoof_calm", 8), "spoofs_caught_16": rate("spoof_calm", 16),
                     "layered_caught_16": rate("layer_calm", 16), "genuine_flagged_16": rate("control_calm", 16),
                     "auc_spoof_vs_normal_16": area("spoof_calm", "normal", 16),
                     "auc_spoof_vs_genuine_16": area("spoof_calm", "genuine", 16),
                     "false_alarm_rate": float(fpr.value.iloc[0]), "chance": float(chance.value.iloc[0])})
    out = pd.DataFrame(rows)
    if impact is not None and len(impact):
        for r in impact.itertuples():
            out[f"fill_gain_{r.spoof.replace(' ', '_')}_{r.size_mult}"] = r.fill_gain
            out[f"fill_gain_ci_low_{r.spoof.replace(' ', '_')}_{r.size_mult}"] = r.fill_gain_ci_low
    return out


def run_sensitivity(fresh):
    frames = []
    for i, (name, overrides) in enumerate(MARKETS.items()):
        print(f"== Market: {name} {overrides}")
        specs = dataset_specs(SMALL, sizes=SIZES, regimes=("calm",), seed_base=100_000 * (i + 1))
        data = load_or_simulate(specs, DATA / "sensitivity" / name.replace(" ", "_"), fresh, overrides)
        ev = evaluate(data, ["train_calm"], ["val_calm"], "calm-trained")
        k = key_numbers(ev, impact_rows(data, sizes=SIZES))
        k.insert(0, "market", name)
        frames.append(k)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(RESULTS / "sensitivity.csv", index=False)
    return out


def run_resolution(fresh):
    print("== Resolution: features every step, sequence detectors read 24 steps")
    specs = {k: v for k, v in dataset_specs(SMALL, sizes=SIZES, regimes=("calm",), seed_base=900_000).items()
             if not k.startswith("honest")}
    data = load_or_simulate(specs, DATA / "resolution_1step", fresh, {"bar_steps": 1})
    detectors = make_detectors(sequence=True, width=24, informed=False)
    ev = evaluate(data, ["train_calm"], ["val_calm"], "calm-trained", detectors=detectors)
    k = key_numbers(ev, None)
    shuffled = pd.DataFrame(shuffle_metrics(data, ev, sizes=SIZES))
    k.to_csv(RESULTS / "resolution.csv", index=False)
    shuffled.to_csv(RESULTS / "resolution_shuffle.csv", index=False)
    return k, shuffled


def run_orders(fresh):
    """Untaught Isolation Forest on INDIVIDUAL ORDERS (see src/orders.py)."""
    import pickle
    from src.evaluate import auc, bootstrap_auc_ci
    from src.isolation_forest import IsolationForest
    from src.market import run_session
    from src.orders import ORDER_FEATURES, mark_special_orders, order_table

    print("== Orders: an untaught Isolation Forest on individual orders")
    specs = {k: v for k, v in dataset_specs(SMALL, sizes=SIZES, regimes=("calm",), seed_base=700_000).items()
             if not k.startswith("honest")}
    cache = DATA / "orders"
    cache.mkdir(parents=True, exist_ok=True)
    tables = {}
    for name, spec in specs.items():
        path = cache / f"{name}.pkl"
        if path.exists() and not fresh:
            tables[name] = pickle.loads(path.read_bytes())
            continue
        print(f"  simulating {name} ({len(spec)} sessions)")
        tables[name] = []
        for seed, regime, specials in spec:
            session = run_session(seed, regime, specials)
            tables[name].append(mark_special_orders(order_table(session), session))
        path.write_bytes(pickle.dumps(tables[name]))

    def stack(names):
        # Orders still resting when the session ends keep their lifetime so far (it is at least that long).
        return pd.concat([x.assign(session=i) for n in names for i, x in enumerate(tables[n])], ignore_index=True)

    rows = []
    variants = [("all four features", ORDER_FEATURES),
                ("without lifetime", [f for f in ORDER_FEATURES if f != "log_lifetime"]),
                ("without size", [f for f in ORDER_FEATURES if f != "log_size"])]
    for label, cols in variants:
        train = stack(["train_calm"])
        mean, std = train[cols].mean(), train[cols].std().replace(0, 1)
        z = lambda t: ((t[cols] - mean) / std).to_numpy()
        forest = IsolationForest(n_trees=200, sample_size=256, seed=0).fit(z(train))
        tau = float(np.quantile(forest.score(z(stack(["val_calm"]))), 0.999))   # 1 normal order in 1,000 alerts
        normal = stack(["normal_calm"])
        normal_scores = forest.score(z(normal))
        rng = np.random.default_rng(0)
        normal_sample = rng.choice(normal_scores, size=min(5000, len(normal_scores)), replace=False)
        for m in SIZES:
            spoof = stack([f"spoof_calm_{m}"]).query("role == 'spoof wall'")
            genuine = stack([f"control_calm_{m}"]).query("role == 'genuine large'")
            pieces = stack([f"layer_calm_{m}"]).query("role == 'layered piece'")
            s_spoof, s_gen = forest.score(z(spoof)), forest.score(z(genuine))
            s_piece = forest.score(z(pieces))
            # One score per layered episode: its most unusual piece (an episode's pieces share a session and start).
            piece_eps = (pd.Series(s_piece, index=pieces.index)
                         .groupby([pieces.session.to_numpy(), pieces.start.to_numpy()]).max().to_numpy())
            low, high = bootstrap_auc_ci(s_spoof, s_gen)
            rows.append({"variant": label, "size_mult": m,
                         "auc_spoof_vs_genuine": auc(s_spoof, s_gen), "ci_low": low, "ci_high": high,
                         "auc_spoof_vs_normal": auc(s_spoof, normal_sample),
                         "auc_layered_vs_genuine": auc(piece_eps, s_gen),
                         "auc_layered_vs_normal": auc(piece_eps, normal_sample),
                         "spoof_walls_flagged": float(np.mean(s_spoof > tau)),
                         "layered_flagged": float(np.mean(piece_eps > tau)),
                         "genuine_flagged": float(np.mean(s_gen > tau)),
                         "normal_orders_flagged": float(np.mean(normal_scores > tau)),
                         "n_spoof": len(s_spoof), "n_genuine": len(s_gen), "n_layered": len(piece_eps)})
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "orders.csv", index=False)
    return out


def checks(sens, base):
    """Each headline claim, checked in the main market and in every alternative market."""
    claims = [
        ("Untaught detectors catch at most 30% of 16× single-wall spoofs",
         lambda d: all(d[d.detector == n].spoofs_caught_16.iloc[0] <= 0.30 for n in UNTAUGHT)),
        ("(added after seeing the results) Untaught detectors flag honest 16× orders at least as often as they catch 16× spoofs",
         lambda d: all(d[d.detector == n].genuine_flagged_16.iloc[0] >= d[d.detector == n].spoofs_caught_16.iloc[0]
                       for n in UNTAUGHT)),
        ("The rule catches at least 90% of 8× and 16× single-wall spoofs",
         lambda d: d[d.detector == "Rule"][["spoofs_caught_8", "spoofs_caught_16"]].min(axis=1).iloc[0] >= 0.90),
        ("Layering drops the rule to at most 30% at 16×",
         lambda d: d[d.detector == "Rule"].layered_caught_16.iloc[0] <= 0.30),
        ("No untaught detector tells spoofs from genuine orders (AUC at most 0.6)",
         lambda d: all(d[d.detector == n].auc_spoof_vs_genuine_16.iloc[0] <= 0.60 for n in UNTAUGHT)),
        ("PCA with spoof-informed features flags at least 50% of genuine 16× orders",
         lambda d: d[d.detector == "PCA (informed)"].genuine_flagged_16.iloc[0] >= 0.50),
        ("The 16× wall measurably helps the genuine order fill (CI above zero)",
         lambda d: d["fill_gain_ci_low_single_wall_16"].iloc[0] > 0),
    ]
    markets = [("main experiment", base)] + [(m, sens[sens.market == m]) for m in MARKETS]
    rows = []
    for text, test in claims:
        row = {"claim": text}
        for name, d in markets:
            try:
                row[name] = "holds" if test(d) else "fails"
            except (IndexError, KeyError):
                row[name] = "n/a"
        rows.append(row)
    return pd.DataFrame(rows)


def base_numbers():
    """The same key numbers from the main experiment (results/*.csv), for comparison."""
    m = pd.read_csv(RESULTS / "metrics.csv")
    a = pd.read_csv(RESULTS / "auc.csv")
    imp = pd.read_csv(RESULTS / "impact.csv")
    m, a = m[m.condition == "calm-trained"], a[a.condition == "calm-trained"]
    rows = []
    for det in m.detector.unique():
        def rate(test, size):
            return float(m[(m.detector == det) & (m.test == test) & (m.size_mult == size)].value.iloc[0])
        rows.append({"detector": det, "spoofs_caught_8": rate("spoof_calm", 8), "spoofs_caught_16": rate("spoof_calm", 16),
                     "layered_caught_16": rate("layer_calm", 16), "genuine_flagged_16": rate("control_calm", 16),
                     "auc_spoof_vs_genuine_16": float(a[(a.detector == det) & (a.test == "spoof_calm") &
                                                        (a.against == "genuine") & (a.size_mult == 16)].auc.iloc[0])})
    out = pd.DataFrame(rows)
    r = imp[(imp.spoof == "single wall") & (imp.size_mult == 16)].iloc[0]
    out["fill_gain_ci_low_single_wall_16"] = r.fill_gain_ci_low
    return out


def write_report(sens, res, res_shuffle, orders=None):
    L = ["# Extension experiments", ""]
    if sens is not None:
        table = checks(sens, base_numbers())
        cols = list(table.columns)
        L += ["## Sensitivity: do the conclusions survive a different market?", "",
              "The core experiment was repeated in four alternative simulated markets (20 training sessions, "
              "about 50 episodes per size each). Settings changed: " +
              "; ".join(f"**{k}** ({', '.join(f'{a}={b}' for a, b in v.items())})" for k, v in MARKETS.items()) + ".", "",
              "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for r in table.itertuples(index=False):
            L.append("| " + " | ".join(str(x) for x in r) + " |")
        L += ["", "Key numbers per market:", "",
              "| Market | Detector | Spoofs 8× | Spoofs 16× | Layered 16× | Genuine flagged 16× | AUC spoof vs genuine 16× | Fill gain 16× |",
              "|---|---|---|---|---|---|---|---|"]
        for r in sens.itertuples():
            L.append(f"| {r.market} | {r.detector} | {r.spoofs_caught_8:.0%} | {r.spoofs_caught_16:.0%} | {r.layered_caught_16:.0%} | "
                     f"{r.genuine_flagged_16:.0%} | {r.auc_spoof_vs_genuine_16:.2f} | {r.fill_gain_single_wall_16:+.0%} |")
    if res is not None:
        L += ["", "## Resolution: does a finer view of time let the sequence detectors see the spoof?", "",
              "Features computed every step instead of every 5 steps; sequence detectors read the last 24 steps.", "",
              "| Detector | Spoofs 8× | Spoofs 16× | Layered 16× | Genuine flagged 16× | AUC spoof vs normal 16× | AUC spoof vs genuine 16× | False alarms |",
              "|---|---|---|---|---|---|---|---|"]
        for r in res.itertuples():
            L.append(f"| {r.detector} | {r.spoofs_caught_8:.0%} | {r.spoofs_caught_16:.0%} | {r.layered_caught_16:.0%} | "
                     f"{r.genuine_flagged_16:.0%} | {r.auc_spoof_vs_normal_16:.2f} | {r.auc_spoof_vs_genuine_16:.2f} | {r.false_alarm_rate:.1%} |")
        L += ["", "Order test at 1-step resolution (AUC, intact → shuffled):", "",
              "| Detector | Test | Size | AUC vs normal | AUC vs genuine |", "|---|---|---|---|---|"]
        for (det, test, m), q in res_shuffle.groupby(["detector", "test", "size_mult"], sort=False):
            a, b = q[q["mode"] == "intact"].iloc[0], q[q["mode"] == "shuffled"].iloc[0]
            L.append(f"| {det} | {test} | {m}× | {a.auc_vs_normal:.2f} → {b.auc_vs_normal:.2f} | "
                     f"{a.auc_vs_genuine:.2f} → {b.auc_vs_genuine:.2f} |")
    if orders is not None:
        L += ["", "## Orders: can an untaught detector spot the fake ORDER rather than an unusual market?", "",
              "Isolation Forest trained on every order in normal sessions, described by size, lifetime, fraction filled "
              "and distance from the best price. Threshold: 1 normal order in 1,000 alerts.", "",
              "| Variant | Size | AUC spoof vs genuine | AUC spoof vs normal | AUC layered vs genuine | Spoof walls flagged | Layered flagged | Genuine flagged | Normal orders flagged |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in orders.itertuples():
            L.append(f"| {r.variant} | {r.size_mult}× | {r.auc_spoof_vs_genuine:.2f} ({r.ci_low:.2f}–{r.ci_high:.2f}) | "
                     f"{r.auc_spoof_vs_normal:.2f} | {r.auc_layered_vs_genuine:.2f} | {r.spoof_walls_flagged:.0%} | "
                     f"{r.layered_flagged:.0%} | {r.genuine_flagged:.0%} | {r.normal_orders_flagged:.2%} |")
    (RESULTS / "extensions.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--only", choices=["sensitivity", "resolution", "orders"])
    args = parser.parse_args()
    sens = res = res_shuffle = None
    if args.only in (None, "sensitivity"):
        sens = run_sensitivity(args.fresh)
    elif (RESULTS / "sensitivity.csv").exists():
        sens = pd.read_csv(RESULTS / "sensitivity.csv")
    if args.only in (None, "resolution"):
        res, res_shuffle = run_resolution(args.fresh)
    elif (RESULTS / "resolution.csv").exists():
        res, res_shuffle = pd.read_csv(RESULTS / "resolution.csv"), pd.read_csv(RESULTS / "resolution_shuffle.csv")
    orders = None
    if args.only in (None, "orders"):
        orders = run_orders(args.fresh)
    elif (RESULTS / "orders.csv").exists():
        orders = pd.read_csv(RESULTS / "orders.csv")
    write_report(sens, res, res_shuffle, orders)
    print((RESULTS / "extensions.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
