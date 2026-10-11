"""Part 3: the price of evasion.

    python run_evasion_cost.py           (about 10 minutes; needs run_teaching.py's cached data)

Part 2 built a detector from the legal definition of spoofing. A spoofer who knew about it
could try to dodge it. This script tries the obvious dodges and measures two things for each:
how often the spoofer is still caught, and what the dodge costs the spoofer.

  * PATIENCE   leave the wall up for P more steps after the genuine order trades, so that
               withdrawing it looks unconnected to the trade. Cost: the wall stays exposed
               (lots of it may really trade, which the spoofer never wanted).
  * COVERING   buy back c lots on the wall's side straight after the genuine order trades,
               so the account no longer traded only the other way. Cost: the spoofer undoes
               part of the very trade the spoof was for, and pays the spread to do it.
  * SMALLER WALLS and TWO ACCOUNTS come from Parts 1 and 2 (impact.csv, teaching_*.csv).

Benefit is measured against the honest twin (same seed, no wall): extra lots the spoofer
managed to trade the way it wanted. Detection uses the principle detector at two window
lengths (40 and 160 steps), the rule, and a version of the principle with no fixed window
that judges each withdrawn order over its own life (src/accounts.py, lifetime_scores). Every
threshold lets about 1% of normal trading alert. The order-life version is also checked on
honest trading: false alarms in calm and volatile markets, and the three honest look-alikes.

Results: results/evasion_cost.csv, results/evasion_cost.md, results/figures/fig8_price_of_evasion.png
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src import accounts as A
from src import config as C
from src.evaluate import bootstrap_ci
from src.features import bar_features
from src.market import run_session

ROOT = Path(__file__).parent
RESULTS, DATA = ROOT / "results", ROOT / "data"
SIZES, N_SESSIONS = (8, 16), 40
STRATEGIES = [("no evasion", {}),
              ("patient: 15 steps", {"spoof_patience": 15}), ("patient: 40 steps", {"spoof_patience": 40}),
              ("patient: 80 steps", {"spoof_patience": 80}), ("patient: 160 steps", {"spoof_patience": 160}),
              ("buys back 1 of 3 lots", {"cover_lots": 1}), ("buys back 2 of 3 lots", {"cover_lots": 2}),
              ("buys back all 3 lots", {"cover_lots": 3})]


def seeds(m):
    return [10_000 + 100 * m + i for i in range(N_SESSIONS)]    # the same spoof sessions as Parts 1 and 2


def threshold(cache, window):
    """The principle detector's alert threshold: 1% of normal windows alert (as in Part 2)."""
    val = pickle.loads((DATA / "accounts" / cache / "val_calm.pkl").read_bytes())
    w = np.concatenate([A.window_max(s["rows"], A.principle_score(s["rows"]["X"].astype(float))) for s in val])
    return float(np.quantile(w, 0.99))


def trades_of(session):
    """Every trade with both sides' accounts: (time, resting order, resting account, aggressor, side, price, qty)."""
    ev = session.events
    return ev[ev.kind == "TRADE"]


def lots_traded_as_intended(session, ep):
    """Lots the spoofer traded on the genuine side, minus lots it bought back; and the
    round-trip cost of the buy-back in ticks per lot."""
    tr = trades_of(session)
    acc, side = ep["account"], -ep["wall_side"]                  # the genuine order's side
    t0 = ep["start"]
    window = tr[(tr.time >= t0) & (tr.time <= (ep["end"] if ep["end"] is not None else t0 + 400))]
    # Genuine side: the spoofer's resting small order was hit, or it crossed the spread at once.
    genuine = window[((window.agent_id == acc) & (window.side == side)) | ((window.aggressor_id == acc) & (window.side == -side))]
    cover = window[(window.aggressor_id == acc) & (window.side == side)]          # it lifted orders on the genuine side = traded the wall's way
    wall_ids = {oid for oid, _ in ep["walls"]}
    wall_hit = window[window.order_id.isin(wall_ids)].qty.sum()
    q_gen, q_cov = genuine.qty.sum(), cover.qty.sum()
    cost = np.nan
    if q_gen and q_cov:
        p_gen = (genuine.price * genuine.qty).sum() / q_gen
        p_cov = (cover.price * cover.qty).sum() / q_cov
        cost = ep["wall_side"] * (p_cov - p_gen)                 # ticks lost per lot on the round trip
    return q_gen - q_cov, wall_hit, cost


def lifetime_threshold():
    """Order-life version: 1% of normal 40-step windows contain an alert (same budget as before)."""
    val = [2000 + i for i in range(10)]                         # the validation seeds of Parts 1 and 2
    w = []
    for seed in val:
        s = run_session(seed, "calm")
        w.append(A.lifetime_window_max(s, *A.lifetime_scores(s)[::2]))
    return float(np.quantile(np.concatenate(w), 0.99))


def lifetime_caught(session, ep, scores, tau):
    c_time, c_acc, sc = scores
    end = ep["end"] if ep["end"] is not None else ep["start"] + C.MAX_EPISODE_STEPS
    mine = (c_acc == ep["account"]) & (c_time >= ep["start"]) & (c_time <= end)
    return bool(mine.any() and sc[mine].max() > tau)


def honest_check(tau):
    """The order-life version on honest trading: false alarms and the honest look-alikes (16x)."""
    out = []
    for regime, base in (("calm", 3000), ("volatile", 53_000)):
        fpr = []
        for i in range(20):
            s = run_session(base + i, regime)
            fpr.append(np.mean(A.lifetime_window_max(s, *A.lifetime_scores(s)[::2]) > tau))
        out.append({"test": f"false alarms, normal {regime} market (share of 40-step windows)", "value": float(np.mean(fpr)), "n": 20})
    for kind, seeds in (("control", [20_000 + 1600 + i for i in range(15)]),
                        ("withdrawal", [45_000 + 1600 + i for i in range(30)]), ("reversal", [40_000 + 1600 + i for i in range(30)])):
        flags = []
        for seed in seeds:
            s = run_session(seed, "calm", [(kind, 16)] * 2)
            sc = A.lifetime_scores(s)
            flags += [lifetime_caught(s, ep, sc, tau) for ep in s.episodes]
        label = {"control": "honest large orders flagged", "withdrawal": "honest quick withdrawals flagged",
                 "reversal": "honest changes of mind flagged"}[kind]
        out.append({"test": f"{label}, 16x", "value": float(np.mean(flags)), "n": len(flags)})
    return pd.DataFrame(out)


def run():
    tau40, tau160 = threshold("main", 40), threshold("accounts_window160", 160)
    tau_life = lifetime_threshold()
    m = pd.read_csv(RESULTS / "metrics.csv")
    tau_rule = float(m[(m.condition == "calm-trained") & (m.detector == "Rule")].threshold.iloc[0])
    print(f"thresholds: principle-40 {tau40:.0f}, principle-160 {tau160:.0f}, order-life {tau_life:.0f}, rule {tau_rule:.0f} lots")
    rows = []
    for size in SIZES:
        twins = {}
        for seed in seeds(size):
            s = run_session(seed, "calm", [("honest", size)] * 2)
            for ep in s.episodes:
                q, _, _ = lots_traded_as_intended(s, ep)
                twins[(seed, ep["start"])] = q
        for name, overrides in STRATEGIES:
            print(f"  {size}x {name}")
            for seed in seeds(size):
                s = run_session(seed, "calm", [("spoof", size)] * 2, overrides)
                r40, r160 = A.account_rows(s, 40), A.account_rows(s, 160)
                p40, p160 = A.principle_score(r40["X"]), A.principle_score(r160["X"])
                rule = bar_features(s)["max_fast_cancel"].to_numpy()
                life = A.lifetime_scores(s)
                for ep in s.episodes:
                    end = ep["end"] if ep["end"] is not None else ep["start"] + C.MAX_EPISODE_STEPS
                    first, last = ep["start"] // s.cfg.bar_steps, (end + s.cfg.bar_steps) // s.cfg.bar_steps + 1
                    q, wall_hit, cost = lots_traded_as_intended(s, ep)
                    twin = twins.get((seed, ep["start"]))
                    rows.append({"strategy": name, "size_mult": size, "seed": seed, "start": ep["start"],
                                 "caught_principle40": A.episode_score(r40, p40, ep["start"], ep["account"], 40) > tau40,
                                 # a patient spoofer's withdrawal can come late: look at windows up to its end
                                 "caught_principle160": A.episode_score(r160, p160, ep["start"], ep["account"], 160) > tau160,
                                 "caught_rule": bool((rule[first:last] > tau_rule).any()),
                                 "caught_lifetime": lifetime_caught(s, ep, life, tau_life),
                                 "lots_as_intended": q, "twin_lots": twin, "wall_lots_traded": wall_hit, "cover_cost_ticks": cost})
    eps = pd.DataFrame(rows)
    eps.to_csv(RESULTS / "evasion_cost_episodes.csv", index=False)
    summary = []
    for (name, size), q in eps.groupby(["strategy", "size_mult"], sort=False):
        gain = (q.lots_as_intended - q.twin_lots).dropna()
        out = {"strategy": name, "size_mult": size, "n": len(q),
               "extra_lots_vs_twin": gain.mean(), "extra_lots_ci_low": bootstrap_ci(gain)[0], "extra_lots_ci_high": bootstrap_ci(gain)[1],
               "wall_lots_traded": q.wall_lots_traded.mean(), "cover_cost_ticks": q.cover_cost_ticks.mean()}
        for det in ("principle40", "principle160", "lifetime", "rule"):
            out[f"caught_{det}"] = q[f"caught_{det}"].mean()
            out[f"caught_{det}_ci_low"], out[f"caught_{det}_ci_high"] = bootstrap_ci(q[f"caught_{det}"])
        summary.append(out)
    summary = pd.DataFrame(summary)
    summary.to_csv(RESULTS / "evasion_cost.csv", index=False)
    honest = honest_check(tau_life)
    honest.to_csv(RESULTS / "evasion_cost_honest.csv", index=False)
    return summary, (tau40, tau160, tau_life, tau_rule), honest


def report(summary, taus, honest):
    tau40, tau160, tau_life, tau_rule = taus
    L = ["# Part 3: the price of evasion", "",
         "Each row is one way a spoofer could try to dodge the principle detector. *Extra lots* is how many more lots the "
         "spoofer traded the way it wanted than its honest twin (same session, no wall): the benefit of spoofing. "
         f"Thresholds: principle detector {tau40:.0f} lots (40-step windows), {tau160:.0f} lots (160-step windows) and "
         f"{tau_life:.0f} lots (each order's own life), rule {tau_rule:.0f} lots; each lets about 1% of normal trading alert.", "",
         "| Strategy | Size | Extra lots vs honest twin (95% CI) | Caught: principle, 40 steps | Caught: principle, 160 steps | Caught: principle, order life | Caught: rule | Wall lots that really traded | Buy-back cost (ticks/lot) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in summary.itertuples():
        cost = "" if pd.isna(r.cover_cost_ticks) else f"{r.cover_cost_ticks:+.2f}"
        L.append(f"| {r.strategy} | {r.size_mult}× | {r.extra_lots_vs_twin:+.2f} ({r.extra_lots_ci_low:+.2f} to {r.extra_lots_ci_high:+.2f}) | "
                 f"{r.caught_principle40:.0%} | {r.caught_principle160:.0%} | {r.caught_lifetime:.0%} | {r.caught_rule:.0%} | "
                 f"{r.wall_lots_traded:.1f} | {cost} |")
    L += ["", "The order-life version on honest trading:", "", "| Test | Value | n |", "|---|---|---|"]
    for r in honest.itertuples():
        L.append(f"| {r.test} | {r.value:.1%} | {r.n} |")
    (RESULTS / "evasion_cost.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def plot(summary):
    """Benefit against the chance of being caught, for every dodge, including smaller walls and two accounts."""
    from src.plots import price_of_evasion
    impact = pd.read_csv(RESULTS / "impact.csv")
    tp = pd.read_csv(RESULTS / "teaching_principle.csv")
    tev = pd.read_csv(RESULTS / "teaching_evasion.csv")
    points = []
    for r in summary[summary.size_mult == 16].itertuples():
        family = "no evasion" if r.strategy == "no evasion" else r.strategy.split(":")[0].split(" ")[0]
        points.append((r.strategy, family, r.caught_lifetime, r.extra_lots_vs_twin))
    for r in impact[impact.spoof == "single wall"].itertuples():
        caught = tp[(tp.setting == "main") & (tp.detector == "Principle (accounts)") & (tp.test == "spoof_calm") &
                    (tp.metric == "catch_rate") & (tp.size_mult == r.size_mult)].value
        if len(caught):
            points.append((f"{r.size_mult}× wall", "smaller", float(caught.iloc[0]), r.fill_gain * C.TYPICAL_SIZE))
    two = tev[tev.setting.str.contains("one account") & (tev.test == "spoof_calm") & (tev.size_mult == 16) & (tev.metric == "catch_rate")]
    base = summary[(summary.strategy == "no evasion") & (summary.size_mult == 16)].extra_lots_vs_twin
    if len(two) and len(base):
        points.append(("two unlinked accounts", "accounts", float(two.value.iloc[0]), float(base.iloc[0])))
    price_of_evasion(points, RESULTS / "figures" / "fig8_price_of_evasion.png")


if __name__ == "__main__":
    s, taus, honest = run()
    report(s, taus, honest)
    plot(s)
    sys.stdout.reconfigure(encoding="utf-8")
    print((RESULTS / "evasion_cost.md").read_text(encoding="utf-8"))
