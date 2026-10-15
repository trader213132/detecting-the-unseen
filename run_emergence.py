"""Reproducible pilot: learning and detector transfer, with held-out causal controls.

python run_emergence.py --workers 4
Existing run_agent.py and its active outputs are deliberately not modified.
The learner chooses an execution configuration once per episode (a policy-gradient
bandit), not an unrestricted sequence of order-book actions or an LLM trader.
"""
import argparse
import hashlib
import json
import platform
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import run_agent as A
import run_challenger as R
from src.market import run_session
from src import config as C

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "emergence"
SOURCE = ["run_emergence.py", "run_agent.py", "run_challenger.py", "src/market.py",
          "src/config.py", "src/orderbook.py", "src/accounts.py", "src/features.py",
          "results/visibility.csv", "results/metrics.csv", "data/accounts/main/val_calm.pkl"]
ENVIRONMENTS = {
    "calm": ("calm", {}),
    "no_feedback": ("calm", {"react_shift": 0., "react_bias": 0., "mm_react_shift": 0.}),
    "volatile": ("volatile", {}),
}
TAUS, WEIGHTS = None, None


def hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE}


def init_worker(taus, weights):
    global TAUS, WEIGHTS
    TAUS, WEIGHTS = taus, np.array(weights)


def ledger(session, ep):
    """Account for both counterparties, including self-matches, in ticks and lots."""
    ev = session.events
    trades = ev[(ev.kind == "TRADE") & (ev.time >= ep["start"]) & (ev.time <= ep["end"])]
    own = (trades.agent_id == ep["account"]).to_numpy(dtype=int)
    aggressor = (trades.aggressor_id == ep["account"]).to_numpy(dtype=int)
    signed = trades.side.to_numpy() * trades.qty.to_numpy() * (own - aggressor)
    inventory = float(signed.sum())
    target = C.TYPICAL_SIZE * ep["task_side"]
    if inventory != target:
        raise ValueError(f"Unfilled inventory: seed={session.seed}, actual={inventory}, target={target}")
    cash = -float(np.dot(signed, trades.price.to_numpy()))
    reward = (cash + target * ep["mid0"]) / C.TYPICAL_SIZE
    volume = float((trades.qty * (own + aggressor)).sum())
    walls = [w[0] for w in ep["walls"]]
    extra_fills = float(trades.loc[trades.order_id.isin(walls), "qty"].sum())
    cancellations = ev[(ev.kind == "CANCEL") & ev.order_id.isin(walls)]
    cancelled_extra = float(cancellations.qty.sum())
    return {"reward": reward, "inventory": inventory, "turnover": volume,
            "extra_filled_lots": extra_fills, "extra_cancelled_lots": cancelled_extra}


def simulate(job):
    action, seed, environment, detect = job
    regime, overrides = ENVIRONMENTS[environment]
    s = run_session(seed, regime, [("agent", 1, action)], overrides={"steps": 600, **overrides})
    if len(s.episodes) != 1:
        raise ValueError("Expected exactly one independent episode per session")
    ep = s.episodes[0]
    row = {"seed": seed, "environment": environment, **action, **ledger(s, ep),
           "signature": bool(A.manipulative(action)), "task_side": ep["task_side"]}
    if detect:
        row.update({f"flag_{k}": bool(v) for k, v in R.judge(s, TAUS, WEIGHTS)[0].items()})
    return row


def ci(values):
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(720231)
    boot = x[rng.integers(0, len(x), size=(4000, len(x)))].mean(axis=1)
    return [float(x.mean()), *map(float, np.quantile(boot, [.025, .975]))]


def evaluate(pool, actions, seeds, environment="calm", detect=True):
    return list(pool.map(simulate, [(a, int(s), environment, detect) for a, s in zip(actions, seeds)], chunksize=8))


def run(args):
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "manifest.json").exists():
        raise SystemExit("This run already has a manifest; use a new output directory, never overwrite evidence.")
    start = time.time()
    before = hashes()
    weights = pd.read_csv(ROOT / "results/visibility.csv").weight.to_numpy()
    taus = R.thresholds(weights)
    manifest = {
        "status": "running", "study": "Restricted execution-policy pilot; not unrestricted emergent manipulation",
        "config": vars(args), "source_sha256": before, "thresholds": taus,
        "training_seed_formula": "20000000 + condition*1000000 + learner*100000 + iteration*batch + sample",
        "validation_seeds": [31000000, 31000000 + args.validation - 1],
        "test_seeds": [32000000, 32000000 + args.test - 1],
        "environments": ENVIRONMENTS, "python": platform.python_version(),
        "numpy": np.__version__, "pandas": pd.__version__, "session_steps": 600,
        "independent_unit": "one episode per market session",
        "reward": "arrival-mid execution surplus per client lot, all extra fills and terminal inventory included",
        "fines": [0., 2.], "learning_rate": A.LR,
        "inference": "paired session bootstrap, pointwise 95% intervals; exploratory, no multiplicity correction",
        "fees": "zero in training; post-hoc turnover cost sensitivity only",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logs, policies, evaluations = [], [], []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker, initargs=(taus, weights.tolist())) as pool:
        val_seeds = range(31000000, 31000000 + args.validation)
        validation = []
        for i, a in enumerate(A.HONEST):
            rows = evaluate(pool, [a] * args.validation, val_seeds, detect=False)
            validation.extend({**r, "baseline": i} for r in rows)
        pd.DataFrame(validation).to_csv(OUT / "baseline_validation.csv", index=False)
        best = max(range(3), key=lambda k: np.mean([r["reward"] for r in validation if r["baseline"] == k]))
        manifest["selected_honest_aggression"] = best
        print(f"Validation-selected baseline: {best}", flush=True)
        for condition, fine in enumerate([0., 2.]):
            for learner in range(args.learners):
                pol = A.Policy(np.random.default_rng([20261014, condition, learner]))
                for iteration in range(args.iterations):
                    choices, actions = zip(*[pol.sample() for _ in range(args.batch)])
                    seeds = [20000000 + condition*1000000 + learner*100000 + iteration*args.batch + j for j in range(args.batch)]
                    rows = evaluate(pool, actions, seeds, detect=fine > 0)
                    scores = np.array([r["reward"] - fine * r.get("flag_seen", False) for r in rows])
                    pol.update(choices, (scores - scores.mean()) / (scores.std() + 1e-9))
                    logs.append({"fine": fine, "learner": learner, "iteration": iteration,
                                 "reward": float(np.mean([r["reward"] for r in rows])), "objective": float(scores.mean()),
                                 "signature_share": float(np.mean([r["signature"] for r in rows])),
                                 **{f"p_{k}_{v}": float(p) for k in A.KNOBS for v, p in zip(A.KNOBS[k], pol.probs(k))}})
                    if iteration % 25 == 0 or iteration == args.iterations - 1:
                        print(f"fine={fine:g} learner={learner+1}/{args.learners} round={iteration+1}/{args.iterations} reward={logs[-1]['reward']:+.3f}", flush=True)
                policies.append({"fine": fine, "learner": learner, "action": pol.greedy(),
                                 "probabilities": {k: pol.probs(k).tolist() for k in A.KNOBS},
                                 "description": A.describe(pol.greedy())})
                pd.DataFrame(logs).to_csv(OUT / "training.csv", index=False)
                (OUT / "policies.json").write_text(json.dumps(policies, indent=2), encoding="utf-8")
        seeds = list(range(32000000, 32000000 + args.test))
        random = A.Policy(np.random.default_rng(7312026))
        candidates = [{"id": "honest", "action": A.HONEST[best]},
                      {"id": "random", "actions": [random.sample()[1] for _ in seeds]},
                      {"id": "designed_control", "action": dict(aggression=0, extra_side=-1, extra_size=16, extra_distance=2, extra_life="fill")}]
        for p in policies:
            tag = f"fine{int(p['fine'])}_learner{p['learner']}"
            candidates.append({"id": tag, "action": p["action"]})
            candidates.append({"id": tag + "_no_extra", "action": {**p["action"], "extra_side": 0}})
            pol = A.Policy(np.random.default_rng([12345, int(p["fine"]), p["learner"]]))
            pol.logits = {k: np.log(np.maximum(p["probabilities"][k], 1e-300)) for k in A.KNOBS}
            candidates.append({"id": tag + "_sampled", "actions": [pol.sample()[1] for _ in seeds]})
        for env in ENVIRONMENTS:
            for candidate in candidates:
                actions = candidate.get("actions", [candidate.get("action")] * args.test)
                rows = evaluate(pool, actions, seeds, env)
                evaluations.extend({**r, "policy": candidate["id"]} for r in rows)
            print(f"Completed held-out controls in {env}", flush=True)
            pd.DataFrame(evaluations).to_csv(OUT / "episodes.csv", index=False)
    if hashes() != before:
        raise RuntimeError("A dependency changed during the run; results must not be presented as reproducible.")
    df = pd.DataFrame(evaluations)
    summaries = []
    for (env, policy), group in df.groupby(["environment", "policy"]):
        g = group.sort_values("seed")
        honest = df[(df.environment == env) & (df.policy == "honest")].sort_values("seed")
        delta = g.reward.to_numpy() - honest.reward.to_numpy()
        mean, low, high = ci(delta)
        row = {"environment": env, "policy": policy, "n": len(g), "reward": float(g.reward.mean()),
               "vs_honest": mean, "ci_low": low, "ci_high": high, "signature_share": float(g.signature.mean()),
               "extra_filled_lots": float(g.extra_filled_lots.mean()), "turnover": float(g.turnover.mean()),
               **{f"flag_{k}": float(g[f"flag_{k}"].mean()) for k in ["rule", "window", "order-life", "seen", "both"]}}
        for fee in [.01, .1]:
            row[f"reward_fee_{fee}"] = float((g.reward - fee*g.turnover/C.TYPICAL_SIZE).mean())
        if policy.startswith("fine") and not policy.endswith(("_sampled", "_no_extra")):
            twin = df[(df.environment == env) & (df.policy == policy + "_no_extra")].sort_values("seed")
            row["extra_effect"], row["extra_ci_low"], row["extra_ci_high"] = ci(g.reward.to_numpy()-twin.reward.to_numpy())
        summaries.append(row)
    pd.DataFrame(summaries).to_csv(OUT / "summary.csv", index=False)
    manifest.update(status="complete", elapsed_seconds=time.time()-start, training_episodes=len(logs)*args.batch,
                    evaluated_episodes=len(df), baseline_validation_episodes=len(validation),
                    completed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), policies=policies)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"COMPLETE: {len(logs)*args.batch} training episodes, {len(df)} evaluation episodes", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--learners", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--validation", type=int, default=96)
    parser.add_argument("--test", type=int, default=128)
    args = parser.parse_args()
    if min(vars(args).values()) < 1 or args.learners > 9 or args.iterations*args.batch > 100000:
        parser.error("Positive counts required; seed allocation supports at most nine learners and 100,000 episodes per learner.")
    run(args)
