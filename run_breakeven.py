"""Break-even pilot: when does a spoof pay?  (Economics proposal, pilot on development seeds only)

    python run_breakeven.py            (about 2-4 minutes on 8+ cores)

Protocol (frozen before this ran): research/breakeven-preregistration.md, fingerprint in research/breakeven-seal.txt.

For every development market cell (liquidity x responsiveness x volatility) and wall size:
  * G  extra lots of the genuine order that traded, against the honest twin (same seed, no wall)
  * U  lots of the spoofer's own wall that really traded
  * net = G - U   (the simulator charges no fees, so C = 0)
  * p  share of attempts each detector flags, with its threshold calibrated on that cell's own normal
       trading so that about 1% of normal 40-step blocks alert
  * F* = max(net, 0) / p   the hypothetical sanction at which the expected payoff reaches zero

The held-out seeds (91 000-91 059) and the reserved cells are NOT run here. After the pilot the predictions
for them are written to research/breakeven-predictions.json and fingerprinted.

Outputs: results/breakeven/episodes.csv, results/breakeven/cells.csv, results/breakeven/summary.md,
         research/breakeven-predictions.json, docs/data/breakeven.js
"""
import hashlib
import json
import sys
from itertools import product
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from src import accounts as A
from src.features import bar_features
from src.market import run_session

ROOT = Path(__file__).parent
OUT = ROOT / "results" / "breakeven"
DEV_SEEDS = [90_000 + i for i in range(60)]
CAL_SEEDS = [93_000 + i for i in range(20)]
HELDOUT_SEEDS = [91_000 + i for i in range(60)]          # sealed: never run by this script
RESERVED_SEEDS = [92_000 + i for i in range(60)]         # sealed: never run by this script
ARRIVALS = [1.0, 1.5, 2.25]
REACTS = [0, 3, 6, 9]
REGIMES = ["calm", "volatile"]
SIZES = [8, 16]
RESERVED = [(a, 4.5, r) for a in (1.25, 1.85) for r in REGIMES]
BLOCK = 40
BOOT = 2000


def overrides(arrival, react):
    k = react / 6.0
    return {"arrival_rate": arrival, "react_shift": float(react), "react_bias": 0.3 * k, "mm_react_shift": 3.0 * k}


def episode_end(ep, horizon=30):
    return ep["end"] if ep["end"] is not None else ep["start"] + horizon


def lots(session, ep):
    """(genuine lots traded, own wall lots traded) for one attempt, over the same span as the earlier study."""
    ev = session.events
    tr = ev[(ev.kind == "TRADE") & (ev.time >= ep["start"]) & (ev.time <= episode_end(ep, 400))]
    acc, side = ep["account"], -ep["wall_side"]
    genuine = tr[(tr.order_id == ep["small_id"]) | ((tr.time == ep["start"]) & (tr.aggressor_id == acc) & (tr.side == -side))].qty.sum()
    walls = {oid for oid, _ in ep["walls"]}
    wall = tr[tr.order_id.isin(walls)].qty.sum() if walls else 0
    return float(genuine), float(wall)


def rule_blocks(session):
    rule = bar_features(session)["max_fast_cancel"].to_numpy()
    b = session.cfg.bar_steps
    n = (session.cfg.steps - A.START) // BLOCK
    per, first = BLOCK // b, A.START // b
    return rule, rule[first:first + n * per].reshape(n, per).max(axis=1)


def calibrate(job):
    """Thresholds for one cell: the 99th percentile of each detector's highest score per normal 40-step block."""
    arrival, react, regime = job
    rule_all, life_all = [], []
    for seed in CAL_SEEDS:
        s = run_session(seed, regime, (), overrides(arrival, react))
        rule_all.append(rule_blocks(s)[1])
        c_time, _, sc = A.lifetime_scores(s)
        life_all.append(A.lifetime_window_max(s, c_time, sc))
    return job, {"rule": float(np.quantile(np.concatenate(rule_all), 0.99)),
                 "order-life": float(np.quantile(np.concatenate(life_all), 0.99))}


def play(job):
    """Every development attempt in one cell for one wall size, against its honest twin."""
    (arrival, react, regime, size), taus = job
    ov = overrides(arrival, react)
    rows = []
    for seed in DEV_SEEDS:
        s = run_session(seed, regime, [("spoof", size)] * 2, ov)
        h = run_session(seed, regime, [("honest", size)] * 2, ov)
        twins = {ep["start"]: lots(h, ep)[0] for ep in h.episodes}
        rule = bar_features(s)["max_fast_cancel"].to_numpy()
        c_time, c_acc, life = A.lifetime_scores(s)
        b = s.cfg.bar_steps
        for ep in s.episodes:
            if ep["start"] not in twins:
                continue
            genuine, wall = lots(s, ep)
            first, last = ep["start"] // b, (episode_end(ep) + b) // b + 1
            mine = (c_acc == ep["account"]) & (c_time >= ep["start"]) & (c_time <= episode_end(ep))
            rows.append({"arrival": arrival, "react": react, "regime": regime, "size": size, "seed": seed,
                         "start": ep["start"], "G": genuine - twins[ep["start"]], "U": wall,
                         "net": genuine - twins[ep["start"]] - wall,
                         "caught_rule": bool((rule[first:last] > taus["rule"]).any()),
                         "caught_life": bool(mine.any() and life[mine].max() > taus["order-life"])})
    return rows


def boot_ci(per_session, rng):
    x = np.asarray(per_session, float)
    if len(x) == 0:
        return (np.nan, np.nan)
    means = x[rng.integers(0, len(x), (BOOT, len(x)))].mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def summarise(ep):
    rng = np.random.default_rng(0)
    out = []
    for key, g in ep.groupby(["arrival", "react", "regime", "size"], sort=True):
        by = g.groupby("seed")
        row = dict(zip(["arrival", "react", "regime", "size"], key), n=len(g))
        for col in ("G", "U", "net"):
            row[col] = float(g[col].mean())
            row[col + "_lo"], row[col + "_hi"] = boot_ci(by[col].mean(), rng)
        for d in ("rule", "life"):
            row["p_" + d] = float(g["caught_" + d].mean())
            pos = max(row["net"], 0.0)
            row["Fstar_" + d] = pos / row["p_" + d] if row["p_" + d] > 0 else (0.0 if pos == 0 else float("inf"))
        row["pays"] = "yes" if row["net_lo"] > 0 else ("no" if row["net_hi"] < 0 else "unclear")
        out.append(row)
    return pd.DataFrame(out)


def design(df):
    a, r, v = df["arrival"].to_numpy(float), df["react"].to_numpy(float), (df["regime"] == "volatile").to_numpy(float)
    return np.column_stack([np.ones(len(df)), a, r, v, r * v])


def predictions(cells):
    pred = {"made": "2026-11-14", "pilot_seeds": [DEV_SEEDS[0], DEV_SEEDS[-1]],
            "heldout_seeds": [HELDOUT_SEEDS[0], HELDOUT_SEEDS[-1]], "reserved_seeds": [RESERVED_SEEDS[0], RESERVED_SEEDS[-1]],
            "development_cells": [], "reserved_cells": []}
    for _, c in cells.iterrows():
        pred["development_cells"].append({k: (c[k] if not isinstance(c[k], (np.floating, np.integer)) else c[k].item())
                                          for k in ("arrival", "react", "regime", "size", "net", "net_lo", "net_hi", "p_life", "p_rule", "pays")})
    for size in SIZES:
        sub = cells[cells["size"] == size]
        X = design(sub)
        coef_net = np.linalg.lstsq(X, sub["net"].to_numpy(float), rcond=None)[0]
        coef_p = np.linalg.lstsq(X, sub["p_life"].to_numpy(float), rcond=None)[0]
        res = sub["net"].to_numpy(float) - X @ coef_net
        sd = float(np.sqrt((res ** 2).sum() / max(len(res) - X.shape[1], 1)))
        for a, r, reg in RESERVED:
            x = design(pd.DataFrame({"arrival": [a], "react": [r], "regime": [reg]}))[0]
            net = float(x @ coef_net)
            pred["reserved_cells"].append({"arrival": a, "react": r, "regime": reg, "size": size, "net": round(net, 4),
                                           "net_band": [round(net - 1.96 * sd, 4), round(net + 1.96 * sd, 4)],
                                           "p_life": round(float(np.clip(x @ coef_p, 0, 1)), 4),
                                           "predicted_sign": "positive" if net > 0 else "not positive"})
        pred[f"model_size_{size}"] = {"terms": ["1", "arrival", "react", "volatile", "react*volatile"],
                                      "net_coef": [round(float(c), 5) for c in coef_net], "residual_sd": round(sd, 5)}
    return pred


def write_summary(cells):
    lines = ["# Break-even pilot (development seeds only)", "",
             "Protocol: `research/breakeven-preregistration.md` (sealed before this ran). Held-out and reserved seeds were not run.", "",
             "Units: lots of the genuine order per attempt. C = 0 (no fees in the simulator). F\\* = max(G − U, 0) / p.", "",
             "| Size | Volatility | Liquidity | Responsiveness | G | U | Net (95% CI) | Pays? | p rule | p order-life | F\\* (order-life) |",
             "|---|---|---|---|---:|---:|---|---|---:|---:|---:|"]
    for _, c in cells.sort_values(["size", "regime", "arrival", "react"]).iterrows():
        lines.append(f"| {c['size']}× | {c['regime']} | {c['arrival']} | {c['react']} | {c.G:+.2f} | {c.U:.2f} | "
                     f"{c.net:+.2f} ({c.net_lo:+.2f} to {c.net_hi:+.2f}) | {c.pays} | {c.p_rule:.0%} | {c.p_life:.0%} | {c.Fstar_life:.2f} |")
    pays = cells.groupby("size")["pays"].value_counts().unstack(fill_value=0)
    lines += ["", "## Count of cells by verdict", "", "| Size | " + " | ".join(pays.columns) + " |",
              "|---|" + "---:|" * len(pays.columns)]
    lines += [f"| {size}× | " + " | ".join(str(v) for v in r) + " |" for size, r in pays.iterrows()]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cells_keys = list(product(ARRIVALS, REACTS, REGIMES))
    with Pool() as pool:
        taus = dict(pool.map(calibrate, cells_keys))
        print("calibrated", len(taus), "cells", flush=True)
        jobs = [((a, r, reg, size), taus[(a, r, reg)]) for (a, r, reg) in cells_keys for size in SIZES]
        rows = [row for chunk in pool.map(play, jobs) for row in chunk]
    ep = pd.DataFrame(rows)
    ep.to_csv(OUT / "episodes.csv", index=False)
    cells = summarise(ep)
    cells.to_csv(OUT / "cells.csv", index=False)
    write_summary(cells)
    pred = predictions(cells)
    pj = ROOT / "research" / "breakeven-predictions.json"
    pj.write_text(json.dumps(pred, indent=1, default=float) + "\n", encoding="utf-8", newline="\n")
    digest = hashlib.sha256(pj.read_bytes()).hexdigest()
    seal = ROOT / "research" / "breakeven-seal.txt"
    text = seal.read_text(encoding="utf-8")
    if "breakeven-predictions.json" not in text:
        seal.write_text(text + f"\n2. breakeven-predictions.json\n   sealed: 2026-11-14 (after the development pilot, before any held-out run)\n   sha256: {digest}\n",
                        encoding="utf-8", newline="\n")
    taus_out = {f"{a}|{r}|{reg}": t for (a, r, reg), t in taus.items()}
    site = {"cells": json.loads(cells.replace([np.inf], None).to_json(orient="records")), "thresholds": taus_out,
            "reserved": pred["reserved_cells"], "seal": (ROOT / "research" / "breakeven-seal.txt").read_text(encoding="utf-8")}
    (ROOT / "docs" / "data" / "breakeven.js").write_text("window.BREAKEVEN = " + json.dumps(site) + ";\n", encoding="utf-8")
    print(cells[["size", "regime", "arrival", "react", "G", "U", "net", "net_lo", "net_hi", "pays", "p_rule", "p_life", "Fstar_life"]].round(3).to_string())
    print("predictions sha256", digest)


if __name__ == "__main__":
    sys.exit(main())
