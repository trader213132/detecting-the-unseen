"""Data for the Surveillance Lab page (docs/surveillance.html).

    python build_surveillance.py

Two things, both from the existing simulator and results. Nothing new is measured here.

1. A matched pair of replays. The SAME seed is run twice:
     * "spoof":    a 16x wall behind the best bid, a small genuine sell at the best ask; the wall
                   is cancelled once the sell fills (the Tribunal pattern);
     * "reversal": an honest trader rests the same 16x order, then changes their mind: cancels it
                   and sells a little (src/market.py, the hardest honest case).
   For each, the order book is rebuilt step by step (build_site.replay_frames) and the account's
   three clauses of the law-informed detector (src/accounts.principle_score) are accumulated
   from the episode's start, step by step, so the page can light each clause as it becomes true.
   The pair is chosen as the first seed where both episodes play out in the usual way and both
   are flagged, which is what happens in about nine in ten cases (results/teaching.md).

2. The episode scores behind results/teaching.md (results/teaching_episodes.csv), for the
   threshold slider: every tested spoof, layered spoof, honest change of mind, honest quick
   withdrawal and genuine large order, at 8x and 16x, with the detector's alert threshold.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_site import replay_frames
from src import config as C
from src.accounts import A_BUY, A_SELL, C_BUY, C_SELL, G_BUY, G_SELL, T_BUY, T_SELL, _activity
from src.market import run_session
from src.orderbook import BUY

ROOT = Path(__file__).parent
OUT = ROOT / "docs" / "data" / "surveillance.js"
SIZE = 16
BEFORE, AFTER = 18, 14


def clause_track(session, ep, t0, t1):
    """Cumulative clause values for the episode's account, at every step t0..t1, counted from
    the episode's start. Buy-side signal is positive (the walls in these replays are bids)."""
    t, acc, field, lots = _activity(session.events)
    mine = (acc == ep["account"]) & (t >= ep["start"])
    t, field, lots = t[mine], field[mine], lots[mine]
    sign = 1 if ep["wall_side"] == BUY else -1
    out = []
    for step in range(t0, t1 + 1):
        x = np.zeros(9)
        upto = t <= step
        np.add.at(x, field[upto], lots[upto])
        shown = sign * ((x[A_BUY] + x[G_BUY]) - (x[A_SELL] + x[G_SELL]))
        withdrawn = sign * (x[C_BUY] - x[C_SELL])
        other_way = sign * (x[T_SELL] - x[T_BUY])
        score = min(shown, withdrawn) if shown > 0 and withdrawn > 0 and other_way > 0 else 0.0
        out.append([int(shown), int(withdrawn), int(other_way), round(float(score), 1)])
    return out


def episode_payload(session, ep, t0, t1):
    _, frames = replay_frames(session, ep, before=ep["start"] - t0, after=t1 - ep["end"], half_window=8)
    return {"kind": ep["kind"], "start": ep["start"], "end": ep["end"], "fill_time": ep["fill_time"],
            "wall_side": "bid" if ep["wall_side"] == BUY else "ask",
            "frames": frames, "clauses": clause_track(session, ep, t0, t1)}


def pick_pair(threshold):
    for seed in range(400, 4000):
        s = run_session(seed, "calm", [("spoof", SIZE)])
        r = run_session(seed, "calm", [("reversal", SIZE)])
        if not s.episodes or not r.episodes:
            continue
        es, er = s.episodes[0], r.episodes[0]
        if es["wall_side"] != BUY or es["start"] != er["start"]:
            continue
        if not es["small_filled"] or not er["small_filled"] or not 6 <= es["end"] - es["start"] <= 16:
            continue
        walls = {oid for oid, _ in es["walls"]}
        cancels = s.events[(s.events.kind == "CANCEL") & s.events.order_id.isin(walls)]
        if len(cancels) != len(walls) or (cancels.time != es["end"]).any():
            continue                                   # part of the wall traded or was pulled early
        t0 = es["start"] - BEFORE
        t1 = max(es["end"], er["end"]) + AFTER
        sp, rv = episode_payload(s, es, t0, t1), episode_payload(r, er, t0, t1)
        if sp["clauses"][-1][3] >= threshold and rv["clauses"][-1][3] >= threshold:
            centre = int(round(s.mid[es["start"]]))
            return seed, centre, sp, rv
    raise RuntimeError("no matched pair found")


def scores():
    d = pd.read_csv(ROOT / "results" / "teaching_episodes.csv")
    d = d[(d.setting == "main") & (d.detector == "Principle (accounts)") & d.size_mult.isin([8, 16])]
    tests = {"spoof_calm": "spoof", "layer_calm": "layer", "reversal_calm": "reversal",
             "withdrawal_calm": "withdrawal", "control_calm": "control"}
    out = {}
    for test, name in tests.items():
        for size in (8, 16):
            out[f"{name}_{size}"] = sorted(round(float(v), 1) for v in d[(d.test == test) & (d.size_mult == size)].score)
    return float(d.threshold.iloc[0]), out


def main():
    threshold, dist = scores()
    seed, centre, spoof, reversal = pick_pair(threshold)
    prices = list(range(centre + 8, centre - 9, -1))
    payload = {"seed": seed, "size_mult": SIZE, "typical": C.TYPICAL_SIZE, "wall": SIZE * C.TYPICAL_SIZE,
               "threshold": threshold, "prices": prices, "spoof": spoof, "reversal": reversal,
               "scores": dist}
    OUT.write_text("window.SURVEILLANCE = " + json.dumps(payload, separators=(",", ":"), default=lambda v: v.item()) + ";\n", encoding="utf-8")
    print("seed", seed, "| spoof", spoof["start"], "->", spoof["end"], "| reversal", reversal["start"], "->", reversal["end"])
    print("final clauses spoof", spoof["clauses"][-1], "reversal", reversal["clauses"][-1], "threshold", threshold)
    print({k: (len(v), sum(x >= threshold for x in v)) for k, v in dist.items()})
    print("wrote", OUT)


if __name__ == "__main__":
    main()
