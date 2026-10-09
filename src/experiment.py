"""Experiment machinery shared by run_experiments.py and run_sensitivity.py.

The flow is always the same:
  1. Simulate sessions with known seeds (normal, spoofed, layered, genuine large orders,
     and honest twins).
  2. Fit every detector on NORMAL training sessions only.
  3. Fix each detector's threshold on NORMAL validation sessions (~1% of bars alert).
  4. Score held-out test sessions and keep one row per episode, so every later
     analysis (catch rates, AUC, paired tests) works from the same evidence.
"""
import pickle
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config as C
from .detectors import (IForestDetector, LSTMAEDetector, PCADetector, RuleDetector,
                        SeqPCADetector)
from .evaluate import (auc, bootstrap_auc_ci, bootstrap_ci, caught, chance_rate,
                       normal_window_maxes, paired_difference, threshold, window_max)
from .features import GENERIC, INFORMED, INFORMED_EXTRA, bar_features, episode_windows
from .market import run_session

SIZES = C.SIZE_MULTIPLIERS
EPISODES_PER_SESSION = 2
FULL = {"train": 30, "val": 10, "normal": 20, "spoof": 40, "layer": 30, "control": 15}
TEST_PREFIXES = ("spoof_", "layer_", "control_")
SEQUENCE_DETECTORS = ("Seq-PCA (generic)", "LSTM-AE (generic)")


# --- 1. Datasets --------------------------------------------------------------
def dataset_specs(n=FULL, sizes=SIZES, regimes=("calm", "volatile"), seed_base=0):
    """name -> list of (seed, regime, specials). Every dataset uses its own seeds."""
    specs = {}
    for regime, base in [("calm", 0), ("volatile", 50_000)]:
        if regime not in regimes:
            continue
        base += seed_base
        for split, offset in [("train", 1000), ("val", 2000), ("normal", 3000)]:
            specs[f"{split}_{regime}"] = [(base + offset + i, regime, ()) for i in range(n[split])]
        for m in sizes:
            seeds = [base + 10_000 + 100 * m + i for i in range(n["spoof"])]
            specs[f"spoof_{regime}_{m}"] = [(s, regime, [("spoof", m)] * EPISODES_PER_SESSION) for s in seeds]
            if regime == "calm":
                # Honest twins: same seeds, same schedule, but no wall.
                specs[f"honest_calm_{m}"] = [(s, regime, [("honest", m)] * EPISODES_PER_SESSION) for s in seeds]
    for m in sizes:
        seeds = [seed_base + 30_000 + 100 * m + i for i in range(n["layer"])]
        specs[f"layer_calm_{m}"] = [(s, "calm", [("layer", m)] * EPISODES_PER_SESSION) for s in seeds]
        specs[f"honest-layer_calm_{m}"] = [(s, "calm", [("honest", m)] * EPISODES_PER_SESSION) for s in seeds]
        specs[f"control_calm_{m}"] = [(seed_base + 20_000 + 100 * m + i, "calm", [("control", m)] * EPISODES_PER_SESSION)
                                      for i in range(n["control"])]
    return specs


def simulate(seed, regime, specials, overrides=None):
    session = run_session(seed, regime, specials, overrides)
    H = C.MAX_EPISODE_STEPS
    episodes = []
    for ep in session.episodes:
        start = ep["start"]
        # Average price shift in the direction the spoofer wants, over the episode.
        shift = ep["wall_side"] * (session.mid[start + 1:start + H + 1].mean() - session.mid[start])
        episodes.append({"kind": ep["kind"], "size_mult": ep["size_mult"], "start": start,
                         "small_filled": ep.get("small_filled"), "shift": shift})
    return {"seed": seed, "features": bar_features(session), "bar_steps": session.cfg.bar_steps,
            "windows": episode_windows(session), "episodes": episodes}


def load_or_simulate(specs, cache_dir, fresh=False, overrides=None, log=print):
    cache_dir.mkdir(parents=True, exist_ok=True)
    data = {}
    for name, spec in specs.items():
        path = cache_dir / f"{name}.pkl"
        if path.exists() and not fresh:
            data[name] = pickle.loads(path.read_bytes())
            continue
        log(f"  simulating {name} ({len(spec)} sessions)")
        data[name] = [simulate(*s, overrides=overrides) for s in spec]
        path.write_bytes(pickle.dumps(data[name]))
    return data


# --- 2-4. Fit, calibrate, score -------------------------------------------------
def make_detectors(sequence=True, width=8, informed=True):
    detectors = [RuleDetector(), PCADetector(GENERIC, "generic")]
    if informed:
        detectors.append(PCADetector(INFORMED, "informed"))
    detectors.append(IForestDetector(GENERIC, "generic"))
    if informed:
        detectors.append(IForestDetector(INFORMED, "informed"))
    if sequence:
        detectors += [SeqPCADetector(GENERIC, "generic", width=width),
                      LSTMAEDetector(GENERIC, "generic", width=width)]
    return detectors


def bar_steps_of(data):
    first = next(iter(data.values()))[0]
    return first.get("bar_steps", C.REGIMES["calm"].bar_steps)


def episode_bars(bar_steps):
    """Length of an episode window in bars (matches features.episode_windows)."""
    return C.MAX_EPISODE_STEPS // bar_steps + 2


def test_name(dataset):
    return dataset.rsplit("_", 1)[0]          # "spoof_calm_8" -> "spoof_calm"


@dataclass
class Evaluation:
    condition: str
    fitted: list = field(default_factory=list)          # (detector, threshold)
    episodes: list = field(default_factory=list)        # one dict per (detector, episode)
    sessions: list = field(default_factory=list)        # one dict per (detector, normal session)
    normal_windows: dict = field(default_factory=dict)  # (detector, regime) -> window maxima / threshold
    chance: dict = field(default_factory=dict)          # (detector, regime) -> chance catch rate


def evaluate(data, train_names, val_names, condition, detectors=None, log=print):
    ev = Evaluation(condition)
    bar_steps = bar_steps_of(data)
    window_bars, skip = episode_bars(bar_steps), 300 // bar_steps
    train = [s["features"] for n in train_names for s in data[n]]
    for det in detectors or make_detectors():
        log(f"  [{condition}] fitting {det.name}")
        det.fit(train)
        tau = threshold(np.concatenate([det.score(s["features"]) for n in val_names for s in data[n]]))
        ev.fitted.append((det, tau))
        for regime in ("calm", "volatile"):
            if f"normal_{regime}" not in data:
                continue
            scores = [det.score(s["features"]) for s in data[f"normal_{regime}"]]
            for i, s in enumerate(scores):
                ev.sessions.append({"detector": det.name, "regime": regime, "session": i,
                                    "fpr": float(np.mean(s > tau))})
            ev.chance[(det.name, regime)] = chance_rate(scores, tau, window_bars)
            ev.normal_windows[(det.name, regime)] = normal_window_maxes(scores, window_bars, max(1, window_bars // 2), skip) / tau
        for name, sessions in data.items():
            if not name.startswith(TEST_PREFIXES):
                continue
            for i, session in enumerate(sessions):
                scores = det.score(session["features"])
                for j, window in enumerate(session["windows"]):
                    segment = scores[window["first_bar"]:window["last_bar"] + 1] > tau
                    ev.episodes.append({
                        "detector": det.name, "test": test_name(name), "size_mult": window["size_mult"],
                        "session": i, "episode": j, "hit": bool(segment.any()),
                        "max_ratio": window_max(scores, window) / tau,
                        "delay_steps": int(np.argmax(segment)) * bar_steps if segment.any() else None})
    return ev


# --- Analyses -----------------------------------------------------------------
def _ci(values):
    low, high = bootstrap_ci(values)
    return {"ci_low": low, "ci_high": high}


def rate_metrics(ev):
    """Catch / flag rates, false alarms, chance levels and delays (one row per number)."""
    rows = []
    taus = {det.name: tau for det, tau in ev.fitted}
    sess = pd.DataFrame(ev.sessions)
    eps = pd.DataFrame(ev.episodes)
    for det, tau in taus.items():
        base = {"condition": ev.condition, "detector": det, "threshold": tau}
        for regime in ("calm", "volatile"):
            q = sess[(sess.detector == det) & (sess.regime == regime)] if len(sess) else sess
            if len(q):
                rows.append({**base, "test": f"normal_{regime}", "metric": "false_alarm_rate", "size_mult": np.nan,
                             "value": q.fpr.mean(), **_ci(q.fpr), "n": len(q)})
                rows.append({**base, "test": f"normal_{regime}", "metric": "chance_catch_rate", "size_mult": np.nan,
                             "value": ev.chance[(det, regime)], "ci_low": np.nan, "ci_high": np.nan, "n": len(q)})
        for (test, m), q in eps[eps.detector == det].groupby(["test", "size_mult"]):
            metric = "flag_rate" if test.startswith("control") else "catch_rate"
            rows.append({**base, "test": test, "metric": metric, "size_mult": m,
                         "value": q.hit.mean(), **_ci(q.hit), "n": len(q)})
            delays = q.delay_steps.dropna()
            if metric == "catch_rate" and len(delays):
                rows.append({**base, "test": test, "metric": "mean_delay_steps", "size_mult": m,
                             "value": delays.mean(), "ci_low": np.nan, "ci_high": np.nan, "n": len(delays)})
    return rows


def auc_metrics(ev, sizes=SIZES):
    """Threshold-free separation. 'vs normal' asks: does an episode look more unusual than an
    ordinary stretch of market? 'vs genuine' asks the sharper question: can the detector tell
    a spoof from an honest large order of the SAME size?"""
    rows = []
    eps = pd.DataFrame(ev.episodes)
    for det, _ in ev.fitted:
        d = eps[eps.detector == det.name]
        for m in sizes:
            def scores(test):
                return d[(d.test == test) & (d.size_mult == m)].max_ratio.to_numpy()
            comparisons = [("spoof_calm", "normal", scores("spoof_calm"), ev.normal_windows.get((det.name, "calm"))),
                           ("layer_calm", "normal", scores("layer_calm"), ev.normal_windows.get((det.name, "calm"))),
                           ("spoof_volatile", "normal", scores("spoof_volatile"), ev.normal_windows.get((det.name, "volatile"))),
                           ("spoof_calm", "genuine", scores("spoof_calm"), scores("control_calm")),
                           ("layer_calm", "genuine", scores("layer_calm"), scores("control_calm"))]
            for test, against, pos, neg in comparisons:
                if neg is None or len(pos) == 0 or len(neg) == 0:
                    continue
                low, high = bootstrap_auc_ci(pos, neg)
                rows.append({"condition": ev.condition, "detector": det.name, "test": test, "against": against,
                             "size_mult": m, "auc": auc(pos, neg), "ci_low": low, "ci_high": high,
                             "n_pos": len(pos), "n_neg": len(neg)})
    return rows


PAIRS = [("Seq-PCA (generic)", "PCA (generic)"),
         ("LSTM-AE (generic)", "IForest (generic)"),
         ("LSTM-AE (generic)", "Seq-PCA (generic)"),
         ("LSTM-AE (generic)", "Rule"),
         ("Rule", "PCA (informed)")]


def paired_metrics(ev, pairs=PAIRS, sizes=(8, 16), tests=("spoof_calm", "layer_calm", "control_calm")):
    """Is detector A's catch rate really different from B's, judged on the same episodes?"""
    eps = pd.DataFrame(ev.episodes)
    names = {det.name for det, _ in ev.fitted}
    rows = []
    for a, b in pairs:
        if a not in names or b not in names:
            continue
        for test in tests:
            for m in sizes:
                key = ["session", "episode"]
                qa = eps[(eps.detector == a) & (eps.test == test) & (eps.size_mult == m)].sort_values(key)
                qb = eps[(eps.detector == b) & (eps.test == test) & (eps.size_mult == m)].sort_values(key)
                if len(qa) == 0 or len(qa) != len(qb):
                    continue
                diff, low, high, p = paired_difference(qa.hit.to_numpy(), qb.hit.to_numpy())
                rows.append({"condition": ev.condition, "test": test, "size_mult": m, "a": a, "b": b,
                             "rate_a": qa.hit.mean(), "rate_b": qb.hit.mean(), "difference": diff,
                             "ci_low": low, "ci_high": high, "p_value": p, "n": len(qa)})
    return rows


def shuffle_metrics(data, ev, sizes=SIZES, seed=7):
    """The order test: score every window again with its bars in a random order.
    If a sequence detector really uses the order of events, its results should drop."""
    rows = []
    for det, tau in ev.fitted:
        if det.name not in SEQUENCE_DETECTORS:
            continue
        bar_steps = bar_steps_of(data)
        window_bars = episode_bars(bar_steps)
        for mode in ("intact", "shuffled"):
            rng = np.random.default_rng(seed)
            shuffle = rng if mode == "shuffled" else None
            normal = [det.score(s["features"], shuffle) for s in data["normal_calm"]]
            neg_normal = normal_window_maxes(normal, window_bars, max(1, window_bars // 2), 300 // bar_steps) / tau
            per_test = {}
            for test in ("spoof_calm", "layer_calm", "control_calm"):
                for m in sizes:
                    hits, maxes = [], []
                    for session in data[f"{test}_{m}"]:
                        scores = det.score(session["features"], shuffle)
                        for window in session["windows"]:
                            hits.append(caught(scores, tau, window))
                            maxes.append(window_max(scores, window) / tau)
                    per_test[(test, m)] = (np.array(hits), np.array(maxes))
            for m in sizes:
                for test in ("spoof_calm", "layer_calm"):
                    hits, maxes = per_test[(test, m)]
                    rows.append({"detector": det.name, "mode": mode, "test": test, "size_mult": m,
                                 "catch_rate": hits.mean(), "auc_vs_normal": auc(maxes, neg_normal),
                                 "auc_vs_genuine": auc(maxes, per_test[("control_calm", m)][1])})
    return rows


def ablation_metrics(data, train_names, val_names, log=print):
    """Which spoof-informed feature carries the 'teaching'? Refit PCA (informed) without
    each one in turn and see what changes."""
    variants = [("all informed features", INFORMED)] + \
               [(f"without {f}", [c for c in INFORMED if c != f]) for f in INFORMED_EXTRA] + \
               [("generic only", GENERIC)]
    rows = []
    for label, columns in variants:
        det = PCADetector(columns, label)
        ev = evaluate(data, train_names, val_names, "ablation", detectors=[det], log=lambda *_: None)
        eps = pd.DataFrame(ev.episodes)

        def rate(test, m):
            return eps[(eps.test == test) & (eps.size_mult == m)].hit.mean()

        spoof16 = eps[(eps.test == "spoof_calm") & (eps.size_mult == 16)].max_ratio
        genuine16 = eps[(eps.test == "control_calm") & (eps.size_mult == 16)].max_ratio
        rows.append({"variant": label, "spoofs_caught_8": rate("spoof_calm", 8), "spoofs_caught_16": rate("spoof_calm", 16),
                     "layered_caught_16": rate("layer_calm", 16), "genuine_flagged_16": rate("control_calm", 16),
                     "auc_spoof_vs_genuine_16": auc(spoof16, genuine16)})
        log(f"  ablation: {label}")
    return rows


def impact_rows(data, sizes=SIZES):
    """What does the wall actually achieve? Compare each spoof episode with the same
    episode in its honest twin session (same seed, same timing, no wall)."""
    rows = []
    for kind, spoof_set, honest_set in [("single wall", "spoof_calm", "honest_calm"),
                                        ("layered", "layer_calm", "honest-layer_calm")]:
        for m in sizes:
            if f"{spoof_set}_{m}" not in data:
                continue
            shift, fill_gain, fills_wall, fills_honest = [], [], [], []
            for with_wall, twin in zip(data[f"{spoof_set}_{m}"], data[f"{honest_set}_{m}"]):
                twin_by_start = {ep["start"]: ep for ep in twin["episodes"]}
                for a in with_wall["episodes"]:
                    b = twin_by_start.get(a["start"])
                    if b is None:
                        continue
                    shift.append(a["shift"] - b["shift"])
                    fill_gain.append(float(a["small_filled"]) - float(b["small_filled"]))
                    fills_wall.append(a["small_filled"])
                    fills_honest.append(b["small_filled"])
            gain_low, gain_high = bootstrap_ci(fill_gain)
            rows.append({"spoof": kind, "size_mult": m, "shift_vs_honest": np.mean(shift), **_ci(shift),
                         "fill_gain": np.mean(fill_gain), "fill_gain_ci_low": gain_low,
                         "fill_gain_ci_high": gain_high, "fill_rate_wall": np.mean(fills_wall),
                         "fill_rate_honest": np.mean(fills_honest), "n": len(shift)})
    return pd.DataFrame(rows)
