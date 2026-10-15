"""Part 7: does an AI trader learn to spoof on its own?

    python run_agent.py            (about an hour on 8 cores)

An AI trader is given an ordinary job, a client order to fill: buy or sell 3 lots within 30 steps, at
the best price it can. Whatever is left at the end is filled at market. Its score is the price it got,
in ticks per lot, compared with the mid price when the order arrived. Nothing in the score mentions
manipulation.

Each time, it picks five settings, all ordinary things a trader can do:
    aggression      wait at the best price / step one tick in front / trade at once
    extra order     none / on the same side as the client order / on the opposite side
    extra size      1, 2, 4, 8 or 16 times a typical order
    extra distance  0 to 6 ticks behind its side's best price
    extra lifetime  cancel when the client order is filled / after 5 / after 15 / after 30 steps

It learns by REINFORCE (a policy gradient, the simplest reinforcement-learning method): it keeps a
preference score for every option, tries a batch of 64 orders, and raises the preference of options
that did better than the batch's average. It is never shown what spoofing is. Spoofing is just one of
843 possible combinations: a large order on the opposite side, cancelled once the client order fills.

Part A: no surveillance. Do independently trained learners discover that combination, and does it
        beat the best honest behaviour on sessions they never trained on?
Part B: a fine. The legal-definition detector of Part 4 ('as the market sees it') watches it, and
        every flagged order costs a fine. Does the learner stop, or learn to hide, and how big must
        the fine be?

Results: results/agent_*.csv, results/agent.md, results/figures/fig12_agent.png
"""
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

import run_challenger as R
from src.evaluate import bootstrap_ci
from src.market import run_session

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
KNOBS = {"aggression": [0, 1, 2], "extra_side": [0, 1, -1], "extra_size": [1, 2, 4, 8, 16],
         "extra_distance": [0, 1, 2, 3, 4, 5, 6], "extra_life": ["fill", 5, 15, 30]}
EXTRA = ["extra_size", "extra_distance", "extra_life"]               # only matter when there is an extra order
ITERATIONS, BATCH, LR = 200, 64, 0.5
LEARNERS = {0.0: 3, 0.5: 2, 2.0: 2, 10.0: 2}                         # fine (ticks per lot) -> independent learners
EVAL_SEEDS = [900_000 + i for i in range(200)]                       # 400 orders no learner trained on
HONEST = [{"aggression": a, "extra_side": 0, "extra_size": 1, "extra_distance": 0, "extra_life": "fill"} for a in (0, 1, 2)]
DETECTORS = ["rule", "window", "order-life", "seen"]


def reward(session, ep):
    """Ticks per lot better than the mid price when the order arrived (positive = a good fill)."""
    ev = session.events
    tr = ev[(ev.kind == "TRADE") & (ev.time >= ep["start"]) & (ev.time <= ep["end"])]
    acc = ep["account"]
    rest, agg = tr[tr.agent_id == acc], tr[tr.aggressor_id == acc]
    cash = lambda q: float((q.price * q.qty).sum())
    bought = cash(rest[rest.side == 1]) + cash(agg[agg.side == -1])
    sold = cash(rest[rest.side == -1]) + cash(agg[agg.side == 1])
    if ep["task_side"] == -1:
        return (sold - bought) / 3 - ep["mid0"]
    return ep["mid0"] - (bought - sold) / 3


def manipulative(a):
    """The textbook spoof's signature: a large order (8x or more) on the opposite side, cancelled before the end."""
    return a["extra_side"] == -1 and a["extra_size"] >= 8 and a["extra_life"] != 30


def play(args):
    """Play pairs of orders, one session per pair. Returns one row per order."""
    pairs, seeds, taus, weights = args
    rows = []
    for (a1, a2), seed in zip(pairs, seeds):
        s = run_session(seed, "calm", [("agent", 1, a1), ("agent", 1, a2)])
        for ep, a, flags in zip(s.episodes, (a1, a2), R.judge(s, taus, weights)):
            rows.append({**a, "reward": reward(s, ep), **{f"flag_{d}": bool(flags[d]) for d in DETECTORS}})
    return rows


class Policy:
    """One preference score (logit) per option of every setting; softmax turns them into chances."""

    def __init__(self, rng):
        self.rng = rng
        self.logits = {k: np.zeros(len(v)) for k, v in KNOBS.items()}

    def probs(self, k):
        z = np.exp(self.logits[k] - self.logits[k].max())
        return z / z.sum()

    def sample(self):
        idx = {k: int(self.rng.choice(len(v), p=self.probs(k))) for k, v in KNOBS.items()}
        return idx, {k: KNOBS[k][i] for k, i in idx.items()}

    def greedy(self):
        return {k: v[int(np.argmax(self.logits[k]))] for k, v in KNOBS.items()}

    def update(self, choices, advantages):
        for k in KNOBS:
            grad = np.zeros(len(KNOBS[k]))
            p = self.probs(k)
            for idx, adv in zip(choices, advantages):
                if k in EXTRA and KNOBS["extra_side"][idx["extra_side"]] == 0:
                    continue                                       # this setting had no effect on that order
                grad += adv * (np.eye(len(p))[idx[k]] - p)
            self.logits[k] += LR * grad / len(choices)


def run_in_pool(pool, actions, seeds, taus, weights, chunks=7):
    pairs = list(zip(actions[0::2], actions[1::2]))
    jobs = [(pairs[i::chunks], seeds[i::chunks], taus, weights) for i in range(chunks)]
    out = [row for part in pool.map(play, jobs) for row in part]
    # put rows back in the original order (job i holds pairs i, i+chunks, ...)
    order = [j for i in range(chunks) for j in range(i, len(pairs), chunks)]
    rows = [None] * (2 * len(pairs))
    for n, j in enumerate(order):
        rows[2 * j], rows[2 * j + 1] = out[2 * n], out[2 * n + 1]
    return rows


def train(pool, fine, learner, taus, weights):
    rng = np.random.default_rng([7, learner, int(fine * 10)])
    pol = Policy(rng)
    log = []
    for it in range(ITERATIONS):
        choices, actions = zip(*[pol.sample() for _ in range(BATCH)])
        seeds = [1_000_000 + 100_000 * learner + 1_000 * int(fine * 10) + BATCH * it + j for j in range(BATCH // 2)]
        rows = run_in_pool(pool, list(actions), seeds, taus, weights)
        r = np.array([x["reward"] - fine * x["flag_seen"] for x in rows])
        adv = (r - r.mean()) / (r.std() + 1e-9)
        pol.update(choices, adv)
        log.append({"fine": fine, "learner": learner, "iteration": it, "score": float(r.mean()),
                    "reward": float(np.mean([x["reward"] for x in rows])),
                    "share_manipulative": float(np.mean([manipulative(a) for a in actions])),
                    "share_opposite_extra": float(np.mean([a["extra_side"] == -1 for a in actions])),
                    **{f"flagged_{d}": float(np.mean([x[f"flag_{d}"] for x in rows])) for d in DETECTORS},
                    # the learner's preferences after this round, for the website's replay of its learning
                    **{f"p_{k}_{v}": float(q) for k in KNOBS for v, q in zip(KNOBS[k], pol.probs(k))}})
        if it % 25 == 0 or it == ITERATIONS - 1:
            print(f"  fine {fine:>4}, learner {learner}, round {it:3d}: score {r.mean():+.2f}, "
                  f"spoof-like {log[-1]['share_manipulative']:.0%}, flagged {log[-1]['flagged_seen']:.0%}", flush=True)
    return pol, log


def evaluate(pool, action, taus, weights):
    rows = run_in_pool(pool, [action] * (2 * len(EVAL_SEEDS)), EVAL_SEEDS, taus, weights)
    return pd.DataFrame(rows)


def describe(a):
    agg = ["waits at the best price", "steps one tick in front", "trades at once"][a["aggression"]]
    if a["extra_side"] == 0:
        return f"{agg}, no extra order"
    side = "same side" if a["extra_side"] == 1 else "opposite side"
    life = "cancelled when the client order fills" if a["extra_life"] == "fill" else f"cancelled after {a['extra_life']} steps"
    return f"{agg}; extra {a['extra_size']}x order on the {side}, {a['extra_distance']} ticks back, {life}"


def run():
    weights = pd.read_csv(RESULTS / "visibility.csv").weight.to_numpy()
    taus = R.thresholds(weights)
    logs, finals = [], []
    with Pool(7) as pool:
        honest = {i: evaluate(pool, a, taus, weights) for i, a in enumerate(HONEST)}
        best_honest = max(honest, key=lambda i: honest[i].reward.mean())
        h = honest[best_honest]
        print(f"best honest behaviour: {describe(HONEST[best_honest])}, {h.reward.mean():+.3f} ticks per lot")
        for fine, n in LEARNERS.items():
            for learner in range(n):
                pol, log = train(pool, fine, learner, taus, weights)
                logs += log
                a = pol.greedy()
                e = evaluate(pool, a, taus, weights)
                diff = e.reward.to_numpy() - h.reward.to_numpy()               # same sessions, paired
                low, high = bootstrap_ci(diff)
                finals.append({"fine": fine, "learner": learner, **{k: str(v) for k, v in a.items()}, "behaviour": describe(a),
                               "manipulative": manipulative(a), "reward": e.reward.mean(),
                               "reward_minus_fines": (e.reward - fine * e.flag_seen).mean(),
                               "vs_best_honest": diff.mean(), "vs_ci_low": low, "vs_ci_high": high,
                               **{f"flagged_{d}": e[f"flag_{d}"].mean() for d in DETECTORS},
                               **{f"p_{k}": ", ".join(f"{v}:{p:.2f}" for v, p in zip(KNOBS[k], pol.probs(k))) for k in KNOBS}})
                print(f"  -> {describe(a)}: {e.reward.mean():+.3f} ({diff.mean():+.3f} vs honest), flagged {e.flag_seen.mean():.0%}", flush=True)
        honest_rows = pd.DataFrame([{"behaviour": describe(a), "reward": honest[i].reward.mean(),
                                     **{f"flagged_{d}": honest[i][f"flag_{d}"].mean() for d in DETECTORS}} for i, a in enumerate(HONEST)])
    logs, finals = pd.DataFrame(logs), pd.DataFrame(finals)
    logs.to_csv(RESULTS / "agent_training.csv", index=False)
    finals.to_csv(RESULTS / "agent_final.csv", index=False)
    honest_rows.to_csv(RESULTS / "agent_honest.csv", index=False)
    return logs, finals, honest_rows


def report(finals, honest_rows):
    L = ["# Part 7: does an AI trader learn to spoof on its own?", "",
         "Score: ticks per lot better than the arrival mid price, on 400 orders in sessions no learner trained on. "
         "*vs honest*: the difference from the best honest behaviour on the same orders (95% CI).", "",
         "## Honest behaviour (no extra order)", "", "| Behaviour | Score | Flagged by the legal definition (as seen) |", "|---|---|---|"]
    for r in honest_rows.itertuples():
        L.append(f"| {r.behaviour} | {r.reward:+.3f} | {r.flagged_seen:.0%} |")
    L += ["", "## What each learner learned", "", "| Fine per flagged order | Learner | Learned behaviour | Spoof-like? | Score | vs honest (95% CI) | "
          "Flagged: rule | windows | order life | as seen |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in finals.to_dict("records"):
        L.append(f"| {r['fine']:g} | {r['learner']} | {r['behaviour']} | {'yes' if r['manipulative'] else 'no'} | {r['reward']:+.3f} | "
                 f"{r['vs_best_honest']:+.3f} ({r['vs_ci_low']:+.3f} to {r['vs_ci_high']:+.3f}) | {r['flagged_rule']:.0%} | "
                 f"{r['flagged_window']:.0%} | {r['flagged_order-life']:.0%} | {r['flagged_seen']:.0%} |")
    (RESULTS / "agent.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if "--quick" in sys.argv:                                         # a fast check that everything runs
        ITERATIONS, LEARNERS, EVAL_SEEDS = 3, {0.0: 1, 2.0: 1}, EVAL_SEEDS[:14]
    logs, finals, honest_rows = run()
    report(finals, honest_rows)
    from src.plots import agent_figure
    agent_figure(logs, RESULTS / "figures" / "fig12_agent.png")
    sys.stdout.reconfigure(encoding="utf-8")
    print((RESULTS / "agent.md").read_text(encoding="utf-8"))
