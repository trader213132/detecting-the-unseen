"""Part 4: an AI challenger.

    python run_challenger.py             (about 20 minutes on 8 cores; needs run_teaching.py's cached data)

Part 3 tried the dodges I could think of. Here a search algorithm looks for dodges itself.
It is a small "genetic" search: it starts from 32 random spoofing strategies, keeps the best,
makes changed copies of them ("mutations") and repeats for 20 rounds. A strategy is seven
settings, every one an ordinary thing a trader can do:

    size      how big the wall is (1x to 16x a typical order)
    distance  how many ticks behind the best price it sits (0 = at the best price)
    layers    how many price levels it is split over
    patience  how long it stays up after the genuine order has traded
    cover     how many of the 3 sold lots it buys straight back
    decoy     a second large order on the OTHER side (as a share of the wall's size) ...
    decoy_at  ... this many ticks behind that side's best price, withdrawn with the wall

Its score is what a spoofer cares about: how many lots of its GENUINE order traded, minus anything it
bought back and any of its wall that traded, beyond its honest twin (the same session with only the
genuine order). A caught spoof has its profit confiscated. A decoy's own trades count neither way.
The challenger gamed two earlier versions of this score. Counting every lot the account sold, it
added a real order near the price and simply sold more. Comparing with a twin that ran the same
strategy minus the wall, it added a decoy that hurt the twin, so the wall merely undid self-inflicted
harm. Searches find holes in the scoring as readily as in the detector.
It runs four
searches, each learning only from one detector's alerts (no surveillance, the rule, order-life and
seen); the windowed detector is scored on everything the searches tried:

    nobody     no surveillance at all: how much spoofing can gain
    rule       large order cancelled within 50 steps (Part 1)
    window     the legal definition, 40-step windows (Part 2)
    order-life the legal definition, judged over each order's life (Part 3)
    seen       order-life, measuring the signal as the market sees it (new here; see
               src/accounts.py): each order weighted by how often traders can see a price
               that far from the best, and orders AT the best price left out

The search uses 16 sessions. A search can get stuck on a strategy that is only locally best, so
at the end every strategy tried in ANY round is scored against each detector, and the five best
are re-tested on 40 sessions the search never saw, so a lucky score cannot pass for a real loophole. The script also checks the "seen" version on
honest trading, including a new honest case: a market maker working off a position.

Results: results/challenger*.csv, results/challenger.md, results/figures/fig9_challenger.png
"""
import os
import pickle
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from src import accounts as A
from src import config as C
from src import market as M
from src.evaluate import bootstrap_ci
from src.features import bar_features
from src.market import run_session
from src.orderbook import BUY, SELL, OrderBook

ROOT = Path(__file__).parent
RESULTS, DATA = ROOT / "results", ROOT / "data"
SEARCH_SEEDS = [70_000 + i for i in range(12)]
TEST_SEEDS = [72_000 + i for i in range(40)]
VAL_SEEDS = [2000 + i for i in range(10)]          # the normal validation sessions of Parts 1-3
TARGETS = ["nobody", "rule", "window", "order-life", "seen"]
SEARCHED = ["nobody", "rule", "order-life", "seen"]
DETECTORS = TARGETS[1:]
POP, GENERATIONS, KEEP, CHILDREN = 32, 15, 8, 16
PLAIN = {"size": 16, "distance": -1, "layers": 1, "patience": 0, "cover": 0, "decoy": 0.0, "decoy_at": 0}


# ---- what the market can see -------------------------------------------------------------
def visibility(seeds=VAL_SEEDS, max_d=12):
    """How often is a price d ticks behind the best among the 5 levels a book-reading trader
    looks at? Measured on normal trading: every time a trader reads the book, for each side,
    a price d ticks back is seen if fewer than 5 occupied prices sit in front of it."""
    seen, looks = np.zeros(max_d + 1), 0
    original = OrderBook.imbalance

    def watching(book, n_levels):
        nonlocal looks
        for side in (BUY, SELL):
            prices = sorted(book.levels[side], reverse=(side == BUY))
            if prices:
                ahead = np.abs(np.array(prices) - prices[0])            # ticks behind the best
                seen[:] += np.searchsorted(ahead, np.arange(max_d + 1), side="left") < n_levels
                looks += 1
        return original(book, n_levels)

    OrderBook.imbalance = watching
    try:
        for seed in seeds:
            run_session(seed, "calm")
    finally:
        OrderBook.imbalance = original
    w = seen / looks
    w[0] = 0.0                       # an order AT the best price is the next to trade: a real offer, not a signal
    return w


# ---- detectors -----------------------------------------------------------------------------
def thresholds(weights):
    """Every detector's alert threshold: about 1% of normal 40-step windows alert."""
    m = pd.read_csv(RESULTS / "metrics.csv")
    taus = {"rule": float(m[(m.condition == "calm-trained") & (m.detector == "Rule")].threshold.iloc[0])}
    val = pickle.loads((DATA / "accounts" / "main" / "val_calm.pkl").read_bytes())
    w40 = np.concatenate([A.window_max(s["rows"], A.principle_score(s["rows"]["X"].astype(float))) for s in val])
    taus["window"] = float(np.quantile(w40, 0.99))
    life, seen = [], []
    for seed in VAL_SEEDS:
        s = run_session(seed, "calm")
        life.append(A.lifetime_window_max(s, *A.lifetime_scores(s)[::2]))
        seen.append(A.lifetime_window_max(s, *A.lifetime_scores(s, weights)[::2]))
    taus["order-life"] = float(np.quantile(np.concatenate(life), 0.99))
    taus["seen"] = float(np.quantile(np.concatenate(seen), 0.99))
    return taus


def episode_end(ep):
    return ep["end"] if ep["end"] is not None else ep["start"] + C.MAX_EPISODE_STEPS


def window_caught(rows, scores, ep, tau):
    """Windowed version: the episode account's score in any 40-step window overlapping the episode."""
    s = rows["starts"][rows["win"]]
    mine = (rows["account"] == ep["account"]) & (s > ep["start"] - 40) & (s <= episode_end(ep))
    return bool(mine.any() and scores[mine].max() > tau)


def life_caught(ep, scores, tau, account=None):
    c_time, c_acc, sc = scores
    mine = (c_acc == (account or ep["account"])) & (c_time >= ep["start"]) & (c_time <= episode_end(ep))
    return bool(mine.any() and sc[mine].max() > tau)


def judge(session, taus, weights):
    """For every episode in the session: was it caught by each detector?"""
    rule = bar_features(session)["max_fast_cancel"].to_numpy()
    rows = A.account_rows(session, 40)
    p40 = A.principle_score(rows["X"])
    life, seen = A.lifetime_scores(session), A.lifetime_scores(session, weights)
    out = []
    for ep in session.episodes:
        b = session.cfg.bar_steps
        first, last = ep["start"] // b, (episode_end(ep) + b) // b + 1
        out.append({"rule": bool((rule[first:last] > taus["rule"]).any()),
                    "window": window_caught(rows, p40, ep, taus["window"]),
                    "order-life": life_caught(ep, life, taus["order-life"]),
                    "seen": life_caught(ep, seen, taus["seen"])})
    return out


# ---- what a strategy gains -----------------------------------------------------------------
def net_lots(session, ep):
    """What the spoof is for: lots of the spoofer's GENUINE order that traded (resting, or crossing at
    once when placed), minus anything it bought back and any of its wall that really traded. A decoy's
    own trades count neither way: selling more lots is not what the wall achieves."""
    ev = session.events
    tr = ev[(ev.kind == "TRADE") & (ev.time >= ep["start"]) & (ev.time <= (ep["end"] if ep["end"] is not None else ep["start"] + 400))]
    acc, side = ep["account"], -ep["wall_side"]
    genuine = tr[(tr.order_id == ep["small_id"]) | ((tr.time == ep["start"]) & (tr.aggressor_id == acc) & (tr.side == -side))].qty.sum()
    walls = {oid for oid, _ in ep["walls"]}
    wrong = tr[((tr.aggressor_id == acc) & (tr.side == side)) | tr.order_id.isin(walls)].qty.sum()
    return float(genuine - wrong)


@lru_cache(maxsize=None)
def twin(seed):
    """The honest twin: the same session with only the genuine order (no wall, no decoy, no dodges)."""
    s = run_session(seed, "calm", [("honest", 16)] * 2)
    return {ep["start"]: net_lots(s, ep) for ep in s.episodes}


def overrides(g):
    return {"spoof_distance": g["distance"], "spoof_layers": g["layers"], "spoof_patience": g["patience"],
            "cover_lots": g["cover"], "decoy_frac": g["decoy"], "decoy_distance": g["decoy_at"]}


def play(args):
    """Run one strategy on the given sessions against the honest twins. One row per spoof episode."""
    g, seeds, taus, weights = args
    rows = []
    for seed in seeds:
        s = run_session(seed, "calm", [("spoof", g["size"])] * 2, overrides(g))
        twins = twin(seed)
        for ep, caught in zip(s.episodes, judge(s, taus, weights)):
            if ep["start"] not in twins:
                continue
            gain = net_lots(s, ep) - twins[ep["start"]]
            rows.append({"seed": seed, "start": ep["start"], "gain": gain, **{f"caught_{k}": v for k, v in caught.items()}})
    return pd.DataFrame(rows)


def payoff(rows, target):
    """The spoofer's score: its gain, but a caught spoof loses any profit (it keeps any loss)."""
    if target == "nobody":
        return rows.gain
    return np.where(rows[f"caught_{target}"], np.minimum(rows.gain, 0), rows.gain)


# ---- the search ------------------------------------------------------------------------------
def key(g):
    g = dict(g)
    if g["decoy"] == 0:
        g["decoy_at"] = 0
    return tuple(sorted(g.items()))


def random_strategy(rng):
    return {"size": int(rng.integers(1, 17)), "distance": int(rng.integers(0, 7)), "layers": int(rng.integers(1, 7)),
            "patience": 0 if rng.random() < 0.3 else int(rng.integers(0, 201)),
            "cover": 0 if rng.random() < 0.5 else int(rng.integers(1, 4)),
            "decoy": 0.0 if rng.random() < 0.4 else round(float(rng.uniform(0.2, 1.5)), 1),
            "decoy_at": int(rng.integers(0, 13))}


def mutate(g, rng):
    g = dict(g)
    for name in rng.choice(list(g), size=int(rng.integers(1, 3)), replace=False):
        if name == "size":
            g[name] = int(np.clip(g[name] + rng.integers(-4, 5), 1, 16))
        elif name == "distance":
            g[name] = int(np.clip(max(g[name], 0) + rng.integers(-2, 3), 0, 6))
        elif name == "layers":
            g[name] = int(np.clip(g[name] + rng.integers(-2, 3), 1, 6))
        elif name == "patience":
            g[name] = int(np.clip(g[name] + rng.integers(-60, 61), 0, 200))
        elif name == "cover":
            g[name] = int(rng.integers(0, 4))
        elif name == "decoy":
            g[name] = 0.0 if rng.random() < 0.2 else round(float(np.clip(g[name] + rng.uniform(-0.4, 0.4), 0.1, 1.5)), 1)
        else:
            g[name] = int(np.clip(g[name] + rng.integers(-3, 4), 0, 12))
    return g


def crossover(a, b, rng):
    return {k: (a if rng.random() < 0.5 else b)[k] for k in a}


class Arena:
    """Plays strategies on the search sessions, remembering every result (any target can reuse it)."""

    def __init__(self, pool, taus, weights):
        self.pool, self.taus, self.weights = pool, taus, weights
        self.seen = {}

    def play(self, strategies):
        new = [g for g in {key(g): g for g in strategies}.values() if key(g) not in self.seen]
        jobs = [(g, SEARCH_SEEDS, self.taus, self.weights) for g in new]
        for g, rows in zip(new, self.pool.map(play, jobs)):
            self.seen[key(g)] = (g, rows)
        return [self.seen[key(g)] for g in strategies]


def search(arena, target, seed):
    """The genetic search against one detector. Returns every strategy tried and the best score per round."""
    rng = np.random.default_rng([seed, TARGETS.index(target)])
    scored = {}

    def add(strategies):
        for g, rows in arena.play(strategies):
            scored[key(g)] = (float(np.mean(payoff(rows, target))), g)

    add([PLAIN] + [random_strategy(rng) for _ in range(POP)])
    progress = [max(s for s, _ in scored.values())]
    for _ in range(GENERATIONS):
        parents = [g for _, g in sorted(scored.values(), key=lambda x: -x[0])[:KEEP]]
        kids = []
        for _ in range(CHILDREN):
            a = parents[int(rng.integers(len(parents)))]
            if rng.random() < 0.3:
                a = crossover(a, parents[int(rng.integers(len(parents)))], rng)
            kids.append(mutate(a, rng))
        add(kids)
        progress.append(max(s for s, _ in scored.values()))
    return scored, progress


def describe(g):
    parts = [f"{g['size']}x wall"]
    parts.append("at the best price" if g["distance"] == 0 else
                 ("1-2 ticks back" if g["distance"] < 0 else f"{g['distance']} ticks back"))
    if g["layers"] > 1:
        parts.append(f"in {g['layers']} layers")
    if g["patience"]:
        parts.append(f"kept {g['patience']} step{'s' if g['patience'] != 1 else ''} after the trade")
    if g["cover"]:
        parts.append(f"buys back {g['cover']} lots")
    if g["decoy"]:
        parts.append(f"decoy {g['decoy']:.0%} of the wall, {g['decoy_at']} ticks back on the other side")
    return ", ".join(parts)


# ---- honest trading ----------------------------------------------------------------------------
def honest_check(taus, weights):
    """Every detector on honest trading, and the 'seen' version on standard spoofs."""
    out = []

    def flags(kind, seeds, m, regime="calm"):
        res = {d: [] for d in DETECTORS}
        for seed in seeds:
            s = run_session(seed, regime, [(kind, m)] * 2)
            for caught in judge(s, taus, weights):
                for d in DETECTORS:
                    res[d].append(caught[d])
        return res

    for regime, base in (("calm", 3000), ("volatile", 53_000)):
        res = {d: [] for d in DETECTORS}
        for i in range(20):
            s = run_session(base + i, regime)
            life, seen = A.lifetime_scores(s), A.lifetime_scores(s, weights)
            res["order-life"].append(np.mean(A.lifetime_window_max(s, life[0], life[2]) > taus["order-life"]))
            res["seen"].append(np.mean(A.lifetime_window_max(s, seen[0], seen[2]) > taus["seen"]))
        for d in ("order-life", "seen"):
            out.append({"case": f"normal {regime} market", "kind": "false alarms (share of 40-step windows)",
                        "size_mult": np.nan, "detector": d, "value": float(np.mean(res[d])), "n": 20})
    cases = [("honest large order", "control", lambda m: [20_000 + 100 * m + i for i in range(15)]),
             ("honest quick cancel", "withdrawal", lambda m: [45_000 + 100 * m + i for i in range(30)]),
             ("honest change of mind", "reversal", lambda m: [40_000 + 100 * m + i for i in range(30)]),
             ("market maker working off a position", "skew", lambda m: [65_000 + 100 * m + i for i in range(30)]),
             ("spoof", "spoof", lambda m: [10_000 + 100 * m + i for i in range(40)]),
             ("layered spoof", "layer", lambda m: [30_000 + 100 * m + i for i in range(30)])]
    for label, kind, seeds in cases:
        for m in (8, 16):
            res = flags(kind, seeds(m), m)
            for d in DETECTORS:
                low, high = bootstrap_ci(np.array(res[d], float))
                out.append({"case": label, "kind": "caught" if kind in ("spoof", "layer") else "flagged",
                            "size_mult": m, "detector": d, "value": float(np.mean(res[d])),
                            "ci_low": low, "ci_high": high, "n": len(res[d])})
    return pd.DataFrame(out)


# ---- run everything ----------------------------------------------------------------------------
def run():
    weights = visibility()
    pd.DataFrame({"ticks_behind_best": np.arange(len(weights)), "weight": weights}).to_csv(RESULTS / "visibility.csv", index=False)
    print("visibility weights:", np.round(weights, 2))
    taus = thresholds(weights)
    print("thresholds:", {k: round(v, 1) for k, v in taus.items()})
    with Pool(max(1, min(8, os.cpu_count() or 1) - 1)) as pool:
        arena = Arena(pool, taus, weights)
        finals, progress = [], []
        for target in SEARCHED:
            scored, prog = search(arena, target, seed=4)
            progress += [{"target": target, "generation": i, "best_search_score": v} for i, v in enumerate(prog)]
            print(f"  {target}: searched {len(scored)} strategies, best search score {prog[-1]:.2f}", flush=True)
        (DATA / "challenger_arena.pkl").write_bytes(pickle.dumps(arena.seen))
        for target in TARGETS:
            # Everything the challenger ever tried, scored against this detector.
            pooled = sorted(((float(np.mean(payoff(rows, target))), g) for g, rows in arena.seen.values()), key=lambda x: -x[0])
            scored = {key(g): (v, g) for v, g in pooled}
            best = [g for _, g in pooled[:5]]
            # Re-test the five best on sessions the search never saw, alongside the plain spoof.
            strategies = [PLAIN] + best
            results = pool.map(play, [(g, TEST_SEEDS, taus, weights) for g in strategies])
            for rank, (g, rows) in enumerate(zip(strategies, results)):
                pay = payoff(rows, target)
                low, high = bootstrap_ci(pay)
                g_low, g_high = bootstrap_ci(rows.gain)
                finals.append({"target": target, "rank": rank, "strategy": describe(g), **g,
                               "search_score": next((s for s, h in scored.values() if key(h) == key(g)), np.nan),
                               "payoff": float(np.mean(pay)), "payoff_ci_low": low, "payoff_ci_high": high,
                               "gain": float(rows.gain.mean()), "gain_ci_low": g_low, "gain_ci_high": g_high,
                               **{f"caught_{d}": float(rows[f"caught_{d}"].mean()) for d in DETECTORS}, "n": len(rows)})
        tried = pd.DataFrame([{**g, "strategy": describe(g), "gain": float(r.gain.mean()),
                               **{f"caught_{d}": float(r[f"caught_{d}"].mean()) for d in DETECTORS}}
                              for g, r in arena.seen.values()])
    finals, progress = pd.DataFrame(finals), pd.DataFrame(progress)
    finals.to_csv(RESULTS / "challenger.csv", index=False)
    progress.to_csv(RESULTS / "challenger_progress.csv", index=False)
    tried.to_csv(RESULTS / "challenger_tried.csv", index=False)
    honest = honest_check(taus, weights)
    honest.to_csv(RESULTS / "challenger_honest.csv", index=False)
    return finals, progress, honest, taus, weights


def report(finals, honest, taus, weights):
    L = ["# Part 4: an AI challenger", "",
         f"Thresholds (about 1% of normal 40-step windows alert): rule {taus['rule']:.0f} lots, window {taus['window']:.0f}, "
         f"order-life {taus['order-life']:.0f}, seen {taus['seen']:.1f}.", "",
         "Visibility weights (share of book readings in which a price d ticks behind the best is among the 5 levels seen; "
         "0 at the best price by design): " + ", ".join(f"d={d}: {w:.2f}" for d, w in enumerate(weights)), "",
         "## The challenger's best strategy against each detector (re-tested on 40 unseen sessions)", "",
         "*Payoff*: lots traded the way the spoofer wanted beyond its honest twin, per spoof, with a caught spoof's profit "
         "confiscated. *Plain* is the ordinary 16x spoof.", "",
         "| Against | Strategy | Payoff (95% CI) | Gain if never caught | Caught: rule | window | order-life | seen |",
         "|---|---|---|---|---|---|---|---|"]
    for target in TARGETS:
        q = finals[finals.target == target]
        best = q[q["rank"] > 0].sort_values("payoff", ascending=False).iloc[0]
        plain = q[q["rank"] == 0].iloc[0]
        for label, r in (("plain", plain), ("best found", best)):
            L.append(f"| {target} ({label}) | {r.strategy} | {r.payoff:+.2f} ({r.payoff_ci_low:+.2f} to {r.payoff_ci_high:+.2f}) | "
                     f"{r.gain:+.2f} | {r.caught_rule:.0%} | {r.caught_window:.0%} | {r['caught_order-life']:.0%} | {r.caught_seen:.0%} |")
    L += ["", "## Honest trading and standard spoofs", "", "| Case | Size | Detector | Value | n |", "|---|---|---|---|---|"]
    for r in honest.itertuples():
        size = "" if pd.isna(r.size_mult) else f"{int(r.size_mult)}x"
        L.append(f"| {r.case} ({r.kind}) | {size} | {r.detector} | {r.value:.1%} | {r.n} |")
    (RESULTS / "challenger.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def plot(finals, progress):
    from src.plots import challenger
    challenger(finals, progress, TARGETS, RESULTS / "figures" / "fig9_challenger.png")


if __name__ == "__main__":
    finals, progress, honest, taus, weights = run()
    report(finals, honest, taus, weights)
    plot(finals, progress)
    sys.stdout.reconfigure(encoding="utf-8")
    print((RESULTS / "challenger.md").read_text(encoding="utf-8"))
