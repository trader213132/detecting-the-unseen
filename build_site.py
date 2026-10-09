"""Build the data files the project website reads (docs/data/*.js).

    python run_experiments.py      (first, so results/ and data/ exist)
    python build_site.py

It does two things:
  1. Copies the real results (results/metrics.csv, results/impact.csv) into
     docs/data/results.js for the interactive charts.
  2. Finds two example spoofs in fresh simulated sessions (one single wall, one
     layered), replays the order book step by step, and scores them with the same
     detectors (trained on the same normal sessions as the experiment) for the
     Figure 1 replay. Each example is chosen so that every detector shows its
     MOST COMMON outcome at that size (from results/metrics.csv), so the replay
     cannot be cherry-picked to flatter any detector (see `pick_example`).
"""
import json
import pickle
from datetime import date

import numpy as np
import pandas as pd

from run_experiments import DATA, RESULTS, ROOT
from src.experiment import make_detectors
from src import config as C
from src.evaluate import threshold
from src.features import bar_features, episode_windows
from src.market import run_session
from src.orderbook import BUY, SELL

OUT = ROOT / "docs" / "data"
HALF_WINDOW = 7          # price rows above and below the centre of the ladder
BEFORE, AFTER = 18, 18   # steps shown before the wall appears / after the episode ends


# --- 1. Results ---------------------------------------------------------------
def results_payload():
    m = pd.read_csv(RESULTS / "metrics.csv")
    impact = pd.read_csv(RESULTS / "impact.csv")
    detectors = list(m.detector.unique())

    def rows(q):
        return [[round(r.value, 4), round(r.ci_low, 4), round(r.ci_high, 4), int(r.n)]
                for r in q.sort_values("size_mult").itertuples()]

    catch, fpr, chance = {}, {}, {}
    for condition in m.condition.unique():
        mc = m[m.condition == condition]
        catch[condition] = {
            test: {d: rows(mc[(mc.detector == d) & (mc.test == test) & (mc.metric == metric)])
                   for d in detectors}
            for test, metric in [("spoof_calm", "catch_rate"), ("layer_calm", "catch_rate"),
                                 ("control_calm", "flag_rate"), ("spoof_volatile", "catch_rate")]}
        fpr[condition] = {
            d: {regime: rows(mc[(mc.detector == d) & (mc.test == f"normal_{regime}") &
                                (mc.metric == "false_alarm_rate")])[0]
                for regime in ("calm", "volatile")}
            for d in detectors}
        chance[condition] = {
            regime: round(mc[(mc.test == f"normal_{regime}") & (mc.metric == "chance_catch_rate")].value.mean(), 4)
            for regime in ("calm", "volatile")}

    impact_out = {}
    for spoof, q in impact.groupby("spoof"):
        impact_out[spoof] = [{"size": int(r.size_mult),
                              "shift": [round(r.shift_vs_honest, 3), round(r.ci_low, 3), round(r.ci_high, 3)],
                              "fill_gain": [round(r.fill_gain, 3), round(r.fill_gain_ci_low, 3),
                                            round(r.fill_gain_ci_high, 3)],
                              "fill_wall": round(r.fill_rate_wall, 3),
                              "fill_honest": round(r.fill_rate_honest, 3), "n": int(r.n)}
                             for r in q.sort_values("size_mult").itertuples()]
    thresholds = {condition: {d: round(float(m[(m.condition == condition) & (m.detector == d)].threshold.iloc[0]), 4)
                              for d in detectors}
                  for condition in m.condition.unique()}
    aucs = pd.read_csv(RESULTS / "auc.csv")
    auc_out = {}
    for (condition, test, against, det), q in aucs.groupby(["condition", "test", "against", "detector"]):
        auc_out.setdefault(condition, {}).setdefault(f"{test}|{against}", {})[det] = [
            [round(r.auc, 3), round(r.ci_low, 3), round(r.ci_high, 3)] for r in q.sort_values("size_mult").itertuples()]
    shuffle = pd.read_csv(RESULTS / "shuffle.csv")
    shuffle_out = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
                   for r in shuffle.to_dict("records")]
    paired = pd.read_csv(RESULTS / "paired.csv")
    paired_out = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
                  for r in paired[paired.condition == "calm-trained"].to_dict("records")]
    ablation = pd.read_csv(RESULTS / "ablation.csv")
    ablation_out = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
                    for r in ablation.to_dict("records")]
    n_sessions = sum(len(pickle.loads(f.read_bytes())) for f in DATA.glob("*.pkl"))
    return {"generated": date.today().isoformat(), "sizes": list(C.SIZE_MULTIPLIERS),
            "detectors": detectors, "catch": catch, "fpr": fpr, "chance": chance,
            "impact": impact_out, "thresholds": thresholds, "typical_size": C.TYPICAL_SIZE,
            "auc": auc_out, "shuffle": shuffle_out, "paired": paired_out, "ablation": ablation_out,
            "n_sessions": n_sessions}


# --- 2. Replays -----------------------------------------------------------------
def fitted_detectors():
    train = [s["features"] for s in pickle.loads((DATA / "train_calm.pkl").read_bytes())]
    val = pickle.loads((DATA / "val_calm.pkl").read_bytes())
    fitted = []
    for det in make_detectors():
        det.fit(train)
        tau = threshold(np.concatenate([det.score(s["features"]) for s in val]))
        fitted.append((det, tau))
    return fitted


def score_bars(session, fitted):
    features = bar_features(session)
    return {det.name: det.score(features) / tau for det, tau in fitted}


def typical_outcomes(kind, size=8):
    """detector -> True if it catches MOST spoofs of this kind and size (calm market)."""
    m = pd.read_csv(RESULTS / "metrics.csv")
    test = "spoof_calm" if kind == "spoof" else "layer_calm"
    q = m[(m.condition == "calm-trained") & (m.test == test) & (m.metric == "catch_rate") & (m.size_mult == size)]
    return {r.detector: r.value >= 0.5 for r in q.itertuples()}


def pick_example(kind, fitted, seeds=range(700, 1200)):
    """First session whose episode looks like the experiment's typical outcome:
    the genuine order fills, the wall is pulled right after (not early), and the
    detectors respond the way they most often do at this size."""
    expected = typical_outcomes(kind)
    for seed in seeds:
        session = run_session(seed, "calm", [(kind, 8)])
        if not session.episodes:
            continue
        ep = session.episodes[0]
        duration = ep["end"] - ep["start"]
        if not ep["small_filled"] or not 6 <= duration <= 22:
            continue
        cancels = session.events[(session.events.kind == "CANCEL") &
                                 session.events.order_id.isin([oid for oid, _ in ep["walls"]])]
        if len(cancels) != len(ep["walls"]) or (cancels.time != ep["end"]).any():
            continue                                  # a wall was pulled early or traded
        window = episode_windows(session)[0]
        scores = score_bars(session, fitted)
        alerted = {name: bool((s[window["first_bar"]:window["last_bar"] + 1] > 1).any())
                   for name, s in scores.items()}
        if alerted == expected:
            return seed, session, ep, scores, alerted
    raise RuntimeError(f"no typical {kind} example found")


def replay_frames(session, ep, before=BEFORE, after=AFTER, half_window=HALF_WINDOW):
    """Rebuild the order book step by step from the event log around one episode."""
    cfg = session.cfg
    t0, t1 = max(0, ep["start"] - before), min(cfg.steps - 1, ep["end"] + after)
    centre = int(round(session.mid[ep["start"]]))
    prices = list(range(centre + half_window, centre - half_window - 1, -1))   # top row first
    walls = {oid for oid, _ in ep["walls"]}
    small = ep["small_id"]

    ev = session.events
    times, kinds = ev.time.to_numpy(), ev.kind.to_numpy()
    ids, sides = ev.order_id.to_numpy(), ev.side.to_numpy()
    pxs, qtys = ev.price.to_numpy(), ev.qty.to_numpy()
    orders, i, frames = {}, 0, []
    for t in range(0, t1 + 1):
        traded = 0
        while i < len(ev) and times[i] <= t:
            oid = ids[i]
            if kinds[i] == "ADD":
                orders[oid] = [sides[i], pxs[i], qtys[i]]
            elif kinds[i] == "CANCEL":
                orders.pop(oid, None)
            else:
                traded += qtys[i] if times[i] == t else 0
                if oid in orders:
                    orders[oid][2] -= qtys[i]
                    if orders[oid][2] <= 0:
                        del orders[oid]
            i += 1
        if t < t0:
            continue
        row = {p: [0, 0, 0, 0] for p in prices}           # bid, ask, spoof, genuine
        for oid, (side, price, qty) in orders.items():
            if price in row:
                row[price][0 if side == BUY else 1] += int(qty)
                if oid in walls:
                    row[price][2] += int(qty)
                if oid == small:
                    row[price][3] += int(qty)
        bids = [p for o, (s, p, q) in orders.items() if s == BUY]
        asks = [p for o, (s, p, q) in orders.items() if s == SELL]
        frames.append({"t": t, "rows": [row[p] for p in prices],
                       "bb": max(bids) if bids else None, "ba": min(asks) if asks else None,
                       "mid": round(float(session.mid[t]), 2), "traded": int(traded)})
    return prices, frames


def terrain_payload(session, ep):
    """A longer stretch of the same episode for the 3D landscape in the page header:
    depth at every price (x) and step (z). The fake wall is kept separately so it can
    be coloured."""
    prices, frames = replay_frames(session, ep, before=150, after=70, half_window=11)
    return {"prices": prices, "start": ep["start"], "end": ep["end"],
            "t": [f["t"] for f in frames], "mid": [f["mid"] for f in frames],
            "bid": [[r[0] for r in f["rows"]] for f in frames],
            "ask": [[r[1] for r in f["rows"]] for f in frames],
            "wall": [[r[2] for r in f["rows"]] for f in frames]}


def replay_payload(kind, fitted):
    seed, session, ep, scores, alerted = pick_example(kind, fitted)
    prices, frames = replay_frames(session, ep)
    bar = session.cfg.bar_steps
    t0, t1 = frames[0]["t"], frames[-1]["t"]
    bars = [{"end": (b + 1) * bar - 1,
             "scores": {name: round(float(s[b]), 3) for name, s in scores.items()}}
            for b in range(t0 // bar, t1 // bar + 1)]
    window = episode_windows(session)[0]
    return {"kind": kind, "seed": seed, "size_mult": ep["size_mult"],
            "wall_side": "bid" if ep["wall_side"] == BUY else "ask",
            "wall_size": int(round(ep["size_mult"] * C.TYPICAL_SIZE)),
            "pieces": len(ep["walls"]), "genuine_size": C.TYPICAL_SIZE,
            "start": ep["start"], "end": ep["end"], "fill_time": ep["fill_time"],
            "window_end": (window["last_bar"] + 1) * bar - 1,
            "prices": prices, "frames": frames, "bars": bars, "alerted": alerted,
            "_session": session, "_ep": ep}


def extensions_payload():
    """Robustness results from run_extensions.py, if it has been run."""
    from run_extensions import MARKETS, base_numbers, checks
    out = {}
    if (RESULTS / "sensitivity.csv").exists():
        sens = pd.read_csv(RESULTS / "sensitivity.csv")
        table = checks(sens, base_numbers())
        out["markets"] = ["main experiment"] + list(MARKETS)
        out["market_settings"] = {k: v for k, v in MARKETS.items()}
        out["checks"] = table.to_dict("records")
        out["sensitivity"] = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
                              for r in sens.to_dict("records")]
    if (RESULTS / "resolution.csv").exists():
        out["resolution"] = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
                             for r in pd.read_csv(RESULTS / "resolution.csv").to_dict("records")]
    if (RESULTS / "orders.csv").exists():
        out["orders"] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
                         for r in pd.read_csv(RESULTS / "orders.csv").to_dict("records")]
    return out


def write_js(path, name, payload):
    text = json.dumps(payload, separators=(",", ":"), default=lambda x: x.item())   # numpy scalars
    path.write_text(f"window.{name} = {text};\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write_js(OUT / "results.js", "RESULTS", results_payload())
    write_js(OUT / "extensions.js", "EXTENSIONS", extensions_payload())
    if "--data-only" in __import__("sys").argv:
        return
    fitted = fitted_detectors()
    replays = {kind: replay_payload(kind, fitted) for kind in ("spoof", "layer")}
    write_js(OUT / "terrain.js", "TERRAIN", terrain_payload(replays["spoof"]["_session"], replays["spoof"]["_ep"]))
    for r in replays.values():
        del r["_session"], r["_ep"]
    write_js(OUT / "replay.js", "REPLAY", replays)
    for kind, r in replays.items():
        print(f"{kind}: seed {r['seed']}, {len(r['frames'])} frames, wall {r['wall_size']} lots "
              f"in {r['pieces']} order(s), alerted {r['alerted']}")
    print("wrote", OUT / "results.js", "and", OUT / "replay.js")


if __name__ == "__main__":
    main()
