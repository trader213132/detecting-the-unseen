"""One slide-ready figure of the break-even pilot (results/breakeven/cells.csv).

    python make_pilot_figure.py

Net payoff G - U of a 16x fake order against its honest twin, in lots of the genuine order per attempt,
with 95% bootstrap intervals, for every development cell. Development data only: the held-out seeds are
sealed and have not been run, so this is not a validated result.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).parent
OUT = ROOT / "results" / "breakeven" / "fig_pilot_net_payoff.png"
MARK, INK, INK2, INK3, LINE = "#c42a68", "#14171f", "#434a58", "#8f97a5", "#d3d7df"


def main():
    d = pd.read_csv(ROOT / "results" / "breakeven" / "cells.csv")
    d = d[d["size"] == 16]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True, dpi=200)
    shades = {1.0: INK3, 1.5: INK2, 2.25: INK}
    for ax, regime in zip(axes, ("calm", "volatile")):
        sub = d[d.regime == regime]
        ax.axhline(0, color=INK, lw=0.9)
        for k, (arrival, g) in enumerate(sorted(sub.groupby("arrival"), key=lambda x: x[0])):
            g = g.sort_values("react")
            x = g.react + (k - 1) * 0.45
            ax.plot(x, g.net, color=shades[arrival], lw=1, alpha=0.5)
            for xi, row in zip(x, g.itertuples()):
                pays = row.pays == "yes"
                ax.plot([xi, xi], [row.net_lo, row.net_hi], color=MARK if pays else shades[arrival], lw=1.6)
                ax.plot(xi, row.net, "o", ms=6, color=MARK if pays else shades[arrival],
                        mec="white", mew=0.8, zorder=3)
            ax.plot([], [], "o", color=shades[arrival], label=f"liquidity {arrival:g}")
        ax.set_title(f"{regime} market", loc="left", fontsize=11, color=INK, fontweight="bold")
        ax.set_xticks([0, 3, 6, 9])
        ax.set_xlabel("book responsiveness (how strongly traders react to the book)", fontsize=8.5, color=INK2)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(LINE)
        ax.tick_params(colors=INK2, labelsize=8.5)
        ax.grid(axis="y", color=LINE, lw=0.5, alpha=0.6)
    axes[0].set_ylabel("net payoff G − U\n(lots per attempt, vs honest twin)", fontsize=9, color=INK2)
    axes[0].plot([], [], "o", color=MARK, label="95% interval above zero")
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("When does a fake order pay? Pilot, 16× walls, 24 simulated markets",
                 x=0.01, y=0.985, ha="left", fontsize=12.5, fontweight="bold", color=INK)
    fig.text(0.01, 0.005, "DEVELOPMENT DATA ONLY: held-out seeds sealed and not yet run. G, U in lots; C = 0 (no fees "
             "in the simulator); penalty not included. Source: run_breakeven.py, results/breakeven/cells.csv.",
             fontsize=7.2, color=INK3)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(OUT, facecolor="white")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
