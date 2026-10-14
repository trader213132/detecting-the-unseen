"""Part 6: the price of a false alarm.

    python run_frontier.py          (about 10 minutes on 8 cores; run after run_challenger.py)

Parts 4 and 5 left one gap that no rule closed: a spoof small enough to sit under the alert threshold.
So the real question for a regulator is a trade-off: for each level of false alarms it is willing to
investigate, how much can the best spoofer still gain? This script draws that curve for each detector.

  1. A pool of strategies: the challenger's best against every detector (everything it tried, pooled),
     plus the strategies that gained most with no surveillance and an ordinary spoof.
  2. Each is played on the 12 practice sessions and the 40 unseen sessions, recording every spoof's
     gain and its raw score under each detector (not just caught / not caught).
  3. Normal trading gives each detector's false-alarm rate at any threshold: the share of 40-step
     blocks whose highest score is above it.
  4. For each threshold the spoofer picks its best strategy on the practice sessions (or not to spoof
     at all), and its payoff is measured on the unseen sessions, so a lucky pick cannot flatter it.

Results: results/frontier.csv, results/frontier.md, results/figures/fig11_frontier.png
"""
import pickle
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

import run_challenger as R
from src import accounts as A
from src.features import bar_features
from src.market import run_session

ROOT = Path(__file__).parent
RESULTS, DATA = ROOT / "results", ROOT / "data"
DETS = ["rule", "window", "order-life", "seen"]
NORMAL_SEEDS = [3000 + i for i in range(20)]                    # the normal calm test sessions of Parts 1-5
BLOCK = A.WINDOW


def episode_scores(session, weights):
    """Every spoof episode's highest score under each detector (the same evidence the alerts use)."""
    rule = bar_features(session)["max_fast_cancel"].to_numpy()
    rows = A.account_rows(session, 40)
    p40 = A.principle_score(rows["X"])
    life, seen = A.lifetime_scores(session), A.lifetime_scores(session, weights)
    starts = rows["starts"][rows["win"]]
    out = []
    for ep in session.episodes:
        end, b = R.episode_end(ep), session.cfg.bar_steps
        mine = (rows["account"] == ep["account"]) & (starts > ep["start"] - 40) & (starts <= end)

        def life_max(sc):
            c_time, c_acc, v = sc
            m = (c_acc == ep["account"]) & (c_time >= ep["start"]) & (c_time <= end)
            return float(v[m].max()) if m.any() else 0.0
        out.append({"rule": float(rule[ep["start"] // b:(end + b) // b + 1].max()),
                    "window": float(p40[mine].max()) if mine.any() else 0.0,
                    "order-life": life_max(life), "seen": life_max(seen)})
    return out


def play(args):
    g, seeds, weights = args
    rows = []
    for seed in seeds:
        s = run_session(seed, "calm", [("spoof", g["size"])] * 2, R.overrides(g))
        twins = R.twin(seed)
        for ep, sc in zip(s.episodes, episode_scores(s, weights)):
            if ep["start"] in twins:
                rows.append({"seed": seed, "gain": R.net_lots(s, ep) - twins[ep["start"]], **sc})
    return pd.DataFrame(rows)


def normal_blocks(weights):
    """Each detector's highest score in every 40-step block of normal calm trading."""
    out = {d: [] for d in DETS}
    for seed in NORMAL_SEEDS:
        s = run_session(seed, "calm")
        n = (s.cfg.steps - A.START) // BLOCK
        rule = bar_features(s)["max_fast_cancel"].to_numpy()
        per = BLOCK // s.cfg.bar_steps
        first = A.START // s.cfg.bar_steps
        out["rule"].append(rule[first:first + n * per].reshape(n, per).max(axis=1))
        rows = A.account_rows(s, 40)
        k = (rows["starts"][rows["win"]] - A.START) // BLOCK
        w = np.zeros(n)
        ok = (k >= 0) & (k < n)
        np.maximum.at(w, k[ok], A.principle_score(rows["X"])[ok])
        out["window"].append(w)
        for name, wt in (("order-life", None), ("seen", weights)):
            c_time, _, sc = A.lifetime_scores(s, wt)
            out[name].append(A.lifetime_window_max(s, c_time, sc))
    return {d: np.concatenate(v) for d, v in out.items()}


def pool_of_strategies():
    arena = pickle.loads((DATA / "challenger_arena.pkl").read_bytes())
    picked = {R.key(R.PLAIN): R.PLAIN}
    for target in R.TARGETS:
        ranked = sorted(arena.values(), key=lambda gr: -float(np.mean(R.payoff(
            gr[1].assign(caught_both=gr[1].caught_window | gr[1].caught_seen), target))))
        for g, _ in ranked[:15]:
            picked[R.key(g)] = g
    return list(picked.values())


def frontier(practice, unseen, normal):
    """For each detector and threshold: the false-alarm rate and the best payoff a spoofer keeps."""
    out = []
    for d in DETS:
        taus = np.unique(np.quantile(normal[d], np.linspace(0.80, 1.0, 81)))
        taus = np.r_[taus, normal[d].max() * 4, np.inf]                          # up to "never alert"
        for tau in taus:
            fa = float(np.mean(normal[d] > tau))

            def payoff(rows):
                return float(np.mean(np.where(rows[d] > tau, np.minimum(rows.gain, 0), rows.gain)))
            scores = [payoff(r) for r in practice]
            best = int(np.argmax(scores))
            kept = payoff(unseen[best]) if scores[best] > 0 else 0.0                   # or not spoofing at all
            out.append({"detector": d, "threshold": float(tau), "false_alarm_rate": fa, "best_payoff": kept,
                        "strategy": R.describe(POOL[best]) if scores[best] > 0 else "do not spoof"})
    return pd.DataFrame(out)


def report(table, unwatched):
    L = ["# Part 6: the price of a false alarm", "",
         f"The best payoff with no surveillance at all (chosen on practice sessions, measured on unseen ones): {unwatched:+.2f} lots per spoof.", "",
         "| Detector | False alarms (share of 40-step blocks) | Best payoff a spoofer keeps | Its strategy |", "|---|---|---|---|"]
    for d in DETS:
        q = table[table.detector == d]
        for target in (0.001, 0.005, 0.01, 0.02, 0.05):
            row = q.iloc[(q.false_alarm_rate - target).abs().argmin()]
            L.append(f"| {d} | {row.false_alarm_rate:.1%} | {row.best_payoff:+.2f} | {row.strategy} |")
    (RESULTS / "frontier.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    weights = pd.read_csv(RESULTS / "visibility.csv").weight.to_numpy()
    POOL = pool_of_strategies()
    print(f"{len(POOL)} strategies in the pool")
    with Pool(7) as pool:
        practice = pool.map(play, [(g, R.SEARCH_SEEDS, weights) for g in POOL])
        unseen = pool.map(play, [(g, R.TEST_SEEDS, weights) for g in POOL])
    normal = normal_blocks(weights)
    table = frontier(practice, unseen, normal)
    table.to_csv(RESULTS / "frontier.csv", index=False)
    gains = [float(r.gain.mean()) for r in practice]
    unwatched = float(unseen[int(np.argmax(gains))].gain.mean())
    report(table, unwatched)
    pd.DataFrame([{"unwatched_best_payoff": unwatched}]).to_csv(RESULTS / "frontier_unwatched.csv", index=False)
    from src.plots import frontier_figure
    frontier_figure(table, unwatched, RESULTS / "figures" / "fig11_frontier.png")
    sys.stdout.reconfigure(encoding="utf-8")
    print((RESULTS / "frontier.md").read_text(encoding="utf-8"))
