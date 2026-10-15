"""Figures for the write-up. Every detector keeps one look everywhere:
  colour = model family (Rule blue, PCA orange, Isolation Forest aqua, LSTM autoencoder ink),
  marker = what it sees (circle: one bar; square: a window of 8 bars),
  line   = features (dashed: generic; solid: spoof-informed or hand-written).
The colours were checked with a colour-blindness validator."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import config as C

SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
FAMILY_COLOUR = {"Rule": "#2a78d6", "PCA": "#eb6834", "Seq-PCA": "#eb6834", "IForest": "#1baf7a", "LSTM-AE": INK}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9,
    "text.color": INK, "axes.labelcolor": INK_2, "axes.edgecolor": AXIS,
    "xtick.color": INK_2, "ytick.color": INK_2, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "legend.frameon": False, "lines.linewidth": 1.8, "lines.markersize": 5.5,
})


def style(name):
    family = name.split(" ")[0]
    dashed = "generic" in name
    window = family in ("Seq-PCA", "LSTM-AE")
    return {"color": FAMILY_COLOUR[family], "linestyle": (0, (4, 2)) if dashed else "-",
            "marker": "s" if window else "o", "markerfacecolor": SURFACE if dashed else FAMILY_COLOUR[family],
            "markeredgewidth": 1.4}


def display_name(name):
    return (name.replace("(generic)", "· generic")
                .replace("(informed)", "· spoof-informed")
                .replace("Rule", "Rule (large order cancelled fast)")
                .replace("Seq-PCA", "Sequence PCA")
                .replace("LSTM-AE", "LSTM autoencoder"))


def _size_axis(ax):
    ax.set_xscale("log", base=2)
    ax.set_xticks(C.SIZE_MULTIPLIERS, [f"{m}×" for m in C.SIZE_MULTIPLIERS])
    ax.minorticks_off()
    ax.set_xlabel("Size of the large order (multiples of a typical order)")


def _rate_lines(ax, metrics, condition, test, metric):
    for name in metrics.detector.unique():
        q = metrics[(metrics.condition == condition) & (metrics.detector == name) &
                    (metrics.test == test) & (metrics.metric == metric)].sort_values("size_mult")
        y = 100 * q.value.to_numpy()
        err = [y - 100 * q.ci_low.to_numpy(), 100 * q.ci_high.to_numpy() - y]
        ax.errorbar(q.size_mult, y, yerr=err, capsize=0, elinewidth=0.9,
                    label=display_name(name), **style(name))
    ax.set_ylim(-3, 103)
    ax.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    _size_axis(ax)


def _chance(ax, metrics, condition, regime):
    q = metrics[(metrics.condition == condition) & (metrics.test == f"normal_{regime}") &
                (metrics.metric == "chance_catch_rate")]
    level = 100 * q.value.mean()
    ax.axhline(level, color=MUTED, linestyle=":", linewidth=1.2, zorder=0)
    ax.text(0.02, 0.98, f"dotted line = chance ({level:.0f}%):\ncatch rate from random alerts alone",
            transform=ax.transAxes, color=INK_2, fontsize=7.5, va="top")


def caught_vs_size(metrics, path):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
    _rate_lines(axes[0], metrics, "calm-trained", "spoof_calm", "catch_rate")
    axes[0].set_title("Spoofs caught: single wall\n(the pattern the rule was written for)")
    axes[0].set_ylabel("Episodes with an alert")
    _rate_lines(axes[1], metrics, "calm-trained", "layer_calm", "catch_rate")
    axes[1].set_title("Spoofs caught: layered wall\n(an unseen variant)")
    _rate_lines(axes[2], metrics, "calm-trained", "control_calm", "flag_rate")
    axes[2].set_title("Genuine large orders flagged\n(false alarms)")
    for ax in axes:
        _chance(ax, metrics, "calm-trained", "calm")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Trained on normal calm markets only · threshold fixed so ~1% of normal bars alert",
                 x=0.01, ha="left", fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.96))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def volatile_catch(metrics, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
    for ax, condition, title in [(axes[0], "calm-trained", "Trained on calm markets only"),
                                 (axes[1], "mixed-trained", "Trained on calm + volatile markets")]:
        _rate_lines(ax, metrics, condition, "spoof_volatile", "catch_rate")
        _chance(ax, metrics, condition, "volatile")
        ax.set_title(title)
    axes[0].set_ylabel("Spoofing episodes caught")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Spoofs hidden in a VOLATILE market", x=0.01, ha="left", fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.96))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def false_alarms(metrics, path):
    names = list(metrics.detector.unique())
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    x = np.arange(len(names))
    width = 0.38
    for ax, condition, title in [(axes[0], "calm-trained", "Trained on calm markets only"),
                                 (axes[1], "mixed-trained", "Trained on calm + volatile markets")]:
        for offset, regime, colour in [(-width / 2, "calm", AXIS), (width / 2, "volatile", INK_2)]:
            values = [100 * metrics[(metrics.condition == condition) & (metrics.detector == n) &
                                    (metrics.test == f"normal_{regime}") &
                                    (metrics.metric == "false_alarm_rate")].value.iloc[0] for n in names]
            ax.bar(x + offset, values, width, color=colour, edgecolor=SURFACE, linewidth=1.5,
                   label=f"tested on a {regime} market")
        ax.axhline(1, color=INK, linestyle=(0, (3, 2)), linewidth=1)
        ax.text(-0.45, 1.5, "1% target", ha="left", fontsize=8, color=INK)
        ax.set_xticks(x, [n.replace(" (", "\n(") for n in names], fontsize=8)
        ax.set_title(title)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Normal bars raising an alert (%)")
    axes[1].legend(loc="upper right", fontsize=8)
    fig.suptitle("False alarms in markets with NO spoofing", x=0.01, ha="left", fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def spoof_impact(impact, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
    variants = [("single wall", INK, "-"), ("layered", MUTED, (0, (4, 2)))]
    panels = [(axes[0], "shift_vs_honest", "ci_low", "ci_high", 1,
               "Price moved in the spoofer's favour", "Mid-price shift vs. honest twin (ticks)"),
              (axes[1], "fill_gain", "fill_gain_ci_low", "fill_gain_ci_high", 100,
               "Extra chance the spoofer's genuine order fills", "Fill rate gain vs. honest twin (points)")]
    for ax, column, low_col, high_col, scale, title, ylabel in panels:
        for spoof, colour, dash in variants:
            q = impact[impact.spoof == spoof]
            y = scale * q[column].to_numpy()
            err = [y - scale * q[low_col].to_numpy(), scale * q[high_col].to_numpy() - y]
            ax.errorbar(q.size_mult, y, yerr=err, color=colour, linestyle=dash, marker="o",
                        markerfacecolor=colour if dash == "-" else SURFACE, capsize=0, elinewidth=0.9,
                        label=f"{spoof} spoof")
            ax.text(q.size_mult.iloc[-1] * 1.15, y[-1], spoof, color=INK_2, fontsize=8, va="center")
        ax.axhline(0, color=AXIS, linewidth=1)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        _size_axis(ax)
        ax.set_xlim(right=C.SIZE_MULTIPLIERS[-1] * 2.6)
    axes[0].legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def example_session(session, features, fitted, path):
    cfg = session.cfg
    show = [(det, tau) for det, tau in fitted
            if det.name in ("Rule", "PCA (informed)", "IForest (generic)", "LSTM-AE (generic)")]
    fig, axes = plt.subplots(2 + len(show), 1, figsize=(10, 8.6), sharex=True,
                             gridspec_kw={"height_ratios": [1.4, 1] + [1] * len(show)})
    steps = np.arange(cfg.steps)
    bar_end = (features.bar.to_numpy() + 1) * cfg.bar_steps

    axes[0].plot(steps, session.mid, color=INK, linewidth=1.1)
    axes[0].set_ylabel("Mid price\n(ticks)")
    axes[1].plot(bar_end, features.imbalance, color=INK_2, linewidth=1.0)
    axes[1].axhline(0, color=AXIS, linewidth=0.8)
    axes[1].set_ylabel("Book\nimbalance")

    for ax, (det, tau) in zip(axes[2:], show):
        scores = det.score(features)
        ax.plot(bar_end, scores, linewidth=1.1, color=style(det.name)["color"])
        ax.axhline(tau, color=INK, linestyle=(0, (3, 2)), linewidth=0.9)
        alerts = scores > tau
        ax.scatter(bar_end[alerts], scores[alerts], s=14, color=INK, zorder=3)
        short = {"Rule": "Rule score", "PCA (informed)": "PCA\n(informed)",
                 "IForest (generic)": "IForest\n(generic)", "LSTM-AE (generic)": "LSTM-AE\n(generic)"}
        ax.set_ylabel(short[det.name])
    axes[2].text(0, axes[2].get_ylim()[1], "dashed line = alert threshold · black dots = alerts",
                 fontsize=7.5, color=INK_2, va="bottom")

    for ep in session.episodes:
        end = ep["start"] + C.MAX_EPISODE_STEPS if ep["kind"] == "spoof" else ep["end"]
        for ax in axes:
            if ep["kind"] == "spoof":
                ax.axvspan(ep["start"], end, color=GRID, alpha=0.9, zorder=0, linewidth=0)
            else:
                ax.axvspan(ep["start"], end, facecolor="none", edgecolor=AXIS, hatch="///",
                           zorder=0, linewidth=0)
        label = (f"spoof ({ep['size_mult']}× wall)" if ep["kind"] == "spoof"
                 else f"genuine large order ({ep['size_mult']}×)")
        axes[0].annotate(label, (ep["start"], 1.0), xycoords=("data", "axes fraction"),
                         xytext=(0, 4), textcoords="offset points", fontsize=8, color=INK)
    axes[-1].set_xlabel("Time (steps)")
    axes[0].set_title("One held-out calm session: a spoof and a genuine large order of the same size",
                      pad=16)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def auc_genuine(aucs, path):
    """Can a detector tell a spoof from an honest large order of the same size?"""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    q = aucs[(aucs.condition == "calm-trained") & (aucs.against == "genuine")]
    for ax, test, title in [(axes[0], "spoof_calm", "Single-wall spoof vs genuine order"),
                            (axes[1], "layer_calm", "Layered spoof vs genuine order")]:
        for name in q.detector.unique():
            r = q[(q.detector == name) & (q.test == test)].sort_values("size_mult")
            y = r.auc.to_numpy()
            ax.errorbar(r.size_mult, y, yerr=[y - r.ci_low, r.ci_high - y], capsize=0, elinewidth=0.9,
                        label=display_name(name), **style(name))
        ax.axhline(0.5, color=MUTED, linestyle=":", linewidth=1.2, zorder=0)
        ax.text(0.02, 0.04, "0.5 = cannot tell them apart", transform=ax.transAxes, color=INK_2, fontsize=7.5)
        ax.set_ylim(0, 1.02)
        ax.set_title(title)
        _size_axis(ax)
    axes[0].set_ylabel("AUC (threshold-free)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Trained on normal calm markets only", x=0.01, ha="left", fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0.13, 1, 0.96))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def ladder_of_teaching(rows, path):
    """Part 2. rows: list of (rung label, [(value, low, high) or None] x 5) for the five tests."""
    tests = ["Spoofs caught", "Layered spoofs caught", "Honest large orders\nflagged",
             "Honest quick\nwithdrawals flagged", "Honest changes of mind\nflagged"]
    colours = ["#c42a68", "#c42a68", INK_2, INK_2, MUTED]
    fig, axes = plt.subplots(1, 5, figsize=(11.6, 3.5), sharey=True)
    y = np.arange(len(rows))[::-1]
    for j, ax in enumerate(axes):
        for i, (_, cells) in enumerate(rows):
            cell = cells[j]
            if cell is None:
                continue
            value, low, high = cell
            ax.barh(y[i], value, height=0.55, color=colours[j])
            ax.plot([low, high], [y[i], y[i]], color=INK, linewidth=1, alpha=0.6)
            ax.text(min(max(value, high), 1) + 0.04, y[i], f"{value:.0%}", va="center", fontsize=8.5, color=INK)
        ax.set_xlim(0, 1.3)
        ax.set_axisbelow(True)
        ax.set_xticks([0, 0.5, 1])
        ax.set_xticklabels(["0%", "50%", "100%"])
        ax.set_title(tests[j], fontsize=9)
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([label for label, _ in rows])
    fig.suptitle("The ladder of teaching (16× orders, calm market)", x=0.01, ha="left", fontweight="bold", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def price_of_evasion(points, path):
    """Part 3. points: (label, family, share caught, extra lots traded vs the honest twin)."""
    colours = {"no evasion": "#c42a68", "patient": "#2a78d6", "buys": "#eb6834", "smaller": MUTED, "accounts": "#1baf7a"}
    names = {"no evasion": "No evasion", "patient": "Patient: wall left up\n15 to 160 steps longer", "buys": None,
             "smaller": "Smaller walls (1×, 2×, 4×)", "accounts": "Two unlinked accounts"}
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.add_patch(plt.Rectangle((-0.04, 0.15), 0.42, 0.55, color="#1baf7a", alpha=0.07, zorder=0, linewidth=0))
    ax.text(-0.02, 0.66, "What a spoofer wants:\nbenefit kept, rarely caught", fontsize=7.5, color="#13795a", va="top")
    groups = {}
    for label, family, caught, gain in points:
        if family == "smaller" and label.startswith(("8", "16")):
            continue                                   # 8x and 16x walls are the no-evasion spoofs themselves
        ax.scatter(caught, gain, s=44, color=colours[family], zorder=3)
        groups.setdefault(family, []).append((label, caught, gain))
        if family == "buys":
            ax.annotate(label, (caught, gain), textcoords="offset points", xytext=(8, -3), fontsize=7.4, color=INK_2)
    for family, pts in groups.items():
        if names.get(family) is None:
            continue
        x = np.mean([c for _, c, _ in pts]); y = np.max([g for _, _, g in pts])
        offset = {"patient": (-150, 14), "no evasion": (8, -16), "smaller": (12, -18), "accounts": (12, -12)}[family]
        ax.annotate(names[family], (x, y), textcoords="offset points", xytext=offset, fontsize=7.6, color=colours[family],
                    fontweight="bold", arrowprops=dict(arrowstyle="-", color=colours[family], lw=0.6) if family == "patient" else None)
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.text(1.06, 0.02, "honest twin", fontsize=7, color=MUTED, ha="right", va="bottom")
    ax.set_xlim(-0.04, 1.08)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Spoofs caught by the principle detector (each order judged over its own life)")
    ax.set_ylabel("Extra lots traded vs honest twin")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_title("The price of evasion (16× walls)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


TARGET_COLOUR = {"nobody": MUTED, "rule": "#2a78d6", "window": "#eb6834", "order-life": "#c42a68", "seen": "#1baf7a", "both": "#6a4fc9"}
TARGET_NAME = {"nobody": "No surveillance", "rule": "The rule", "window": "Legal definition, 40-step windows",
               "order-life": "Legal definition, each order's life", "seen": "Legal definition, as the market sees it",
               "both": "Both versions together"}


def challenger(finals, progress, targets, path):
    """Part 4. Left: the search learning, round by round. Right: on unseen sessions, the plain
    spoof's payoff against each detector and the best strategy the challenger found."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 4.8), gridspec_kw={"width_ratios": [1, 1.25]})
    for t in targets:
        q = progress[progress.target == t]
        a.plot(q.generation, q.best_search_score, color=TARGET_COLOUR[t], label=TARGET_NAME[t])
    a.set_xlabel("Round of the search")
    a.set_ylabel("Best payoff so far (lots per spoof)")
    a.set_title("The challenger learning")
    a.legend(fontsize=7, loc="lower right")
    for i, t in enumerate(targets[::-1]):
        q = finals[finals.target == t]
        plain = q[q["rank"] == 0].iloc[0]
        best = q[q["rank"] > 0].sort_values("payoff", ascending=False).iloc[0]
        y = i
        b.plot([plain.payoff, best.payoff], [y, y], color=AXIS, linewidth=1.2, zorder=1)
        b.scatter(plain.payoff, y, s=40, facecolor=SURFACE, edgecolor=TARGET_COLOUR[t], linewidth=1.5, zorder=3)
        b.errorbar(best.payoff, y, xerr=[[best.payoff - best.payoff_ci_low], [best.payoff_ci_high - best.payoff]],
                   fmt="o", color=TARGET_COLOUR[t], markersize=6.5, capsize=2.5, zorder=4)
    b.set_yticks(range(len(targets)))
    b.set_yticklabels([TARGET_NAME[t] for t in targets[::-1]], fontsize=7.6)
    b.axvline(0, color=AXIS, linewidth=1)
    b.set_xlabel("Payoff on 40 unseen sessions (lots per spoof; caught = profit confiscated)")
    b.set_title("What the best strategy keeps")
    b.grid(axis="x", color=GRID, linewidth=0.6)
    b.grid(axis="y", visible=False)
    b.scatter([], [], s=40, facecolor=SURFACE, edgecolor=INK_2, label="ordinary spoof")
    b.scatter([], [], s=40, color=INK_2, label="best found by the challenger")
    b.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def thresholds_figure(market, budget, path):
    """Part 5. Left: fixed vs adaptive thresholds in a volatile market. Right: precision of a desk's alerts."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.8, 4.4), gridspec_kw={"width_ratios": [1.15, 1]})
    dets = list(market.detector.unique())
    y = np.arange(len(dets))[::-1]
    for i, d in enumerate(dets):
        q = market[market.detector == d]
        v = lambda mode, test, metric, m=None: q[(q["mode"] == mode) & (q.test == test) & (q.metric == metric) &
                                                 ((q.size_mult == m) if m else q.size_mult.isna())].value.iloc[0]
        for mode, dy, colour in (("fixed", 0.14, MUTED), ("adaptive", -0.14, "#1baf7a")):
            fa, catch = v(mode, "normal_volatile", "false_alarm_rate"), v(mode, "spoof_volatile", "catch_rate", 16)
            a.barh(y[i] + dy, fa, height=0.26, color=colour, label=f"{mode} threshold" if i == 0 else None)
            a.text(fa + 0.004, y[i] + dy, f"{fa:.0%} false alarms · {catch:.0%} of spoofs caught", va="center", fontsize=6.8, color=INK_2)
    a.set_yticks(y)
    a.set_yticklabels([display_name(d) for d in dets], fontsize=7.6)
    a.set_xlabel("Share of bars alerting in a volatile market (target: 1%)")
    a.set_title("Fixed vs adaptive thresholds")
    a.grid(axis="x", color=GRID, linewidth=0.6)
    a.grid(axis="y", visible=False)
    a.set_xlim(0, max(0.05, a.get_xlim()[1] * 1.9))
    a.legend(fontsize=7, loc="lower right")
    xs = [1, 10, 100]
    for r in budget.itertuples():
        colour = {"Legal definition, as the market sees it": "#1baf7a", "Legal definition, each order's life": "#c42a68",
                  "Legal definition, 40-step windows": "#eb6834"}.get(r.detector, AXIS)
        lw = 2.2 if colour != AXIS else 1.0
        vals = [getattr(r, f"precision_1_in_{n}") for n in xs]
        b.plot(xs, vals, marker="o", color=colour, linewidth=lw, markersize=4 if colour == AXIS else 5.5,
               label=r.detector if colour != AXIS else None, zorder=3 if colour != AXIS else 2)
    b.plot([], [], color=AXIS, marker="o", markersize=4, linewidth=1, label="Detectors taught nothing, and the rule")
    b.set_xscale("log")
    b.set_xticks(xs)
    b.set_xticklabels(["every session", "1 in 10", "1 in 100"])
    b.set_ylim(-0.02, 1.02)
    b.set_yticks([0, 0.25, 0.5, 0.75, 1])
    b.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    b.set_xlabel("How often a 16× spoof happens")
    b.set_ylabel("Alerts that are real spoofs (precision)")
    b.set_title("Of a desk's alerts, how many are real?")
    b.legend(fontsize=6.8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def frontier_figure(table, unwatched, path):
    """Part 6. For each detector: the best payoff a spoofer keeps, against the false alarms the regulator accepts."""
    names = {"rule": "The rule", "window": "Legal definition, 40-step windows",
             "order-life": "Legal definition, each order's life", "seen": "Legal definition, as the market sees it"}
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    floor = 0.0005
    for d in ("rule", "window", "order-life", "seen"):
        q = table[table.detector == d].sort_values("false_alarm_rate")
        x = np.maximum(q.false_alarm_rate.to_numpy(), floor)
        y = q.best_payoff.to_numpy()
        ax.step(x, y, where="post", color=TARGET_COLOUR[d], linewidth=2.4 if d == "seen" else 1.8, label=names[d],
                linestyle=(0, (5, 3)) if d == "window" else "-", zorder=4 if d == "window" else 3)
    ax.axhline(unwatched, color=MUTED, linestyle="--", linewidth=1)
    ax.text(0.00055, unwatched * 1.03, "no surveillance", va="bottom", ha="left", fontsize=7.5, color=MUTED)
    ax.axvline(0.01, color=AXIS, linestyle=":", linewidth=1)
    ax.text(0.0105, unwatched * 1.02, "1% (used in Parts 1-5)", fontsize=7, color=INK_2, va="bottom")
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.set_xscale("log")
    ax.set_xlim(floor, 0.2)
    ax.set_xticks([floor, 0.001, 0.01, 0.1])
    ax.set_xticklabels(["none", "0.1%", "1%", "10%"])
    ax.set_xlabel("False alarms the regulator accepts (share of 40-step blocks of normal trading)")
    ax.set_ylabel("Best payoff a spoofer keeps (lots per spoof)")
    ax.set_title("The price of a false alarm")
    ax.legend(fontsize=7.5, loc="lower left")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def agent_figure(logs, path):
    """Part 7. Left: how often the learner chose the spoof's signature, round by round, for each fine.
    Right: its score. One line per independent learner."""
    fines = sorted(logs.fine.unique())
    colours = dict(zip(fines, ["#c42a68", "#eb6834", "#2a78d6", "#1baf7a"]))
    fig, (a, b) = plt.subplots(1, 2, figsize=(9.8, 4.2))
    for (fine, learner), q in logs.groupby(["fine", "learner"]):
        smooth = q.share_manipulative.rolling(10, min_periods=1).mean()
        a.plot(q.iteration, smooth, color=colours[fine], linewidth=1.8, alpha=0.9,
               label=f"fine {fine:g} ticks/lot" if learner == 0 else None)
        b.plot(q.iteration, q.reward.rolling(10, min_periods=1).mean(), color=colours[fine], linewidth=1.5, alpha=0.9)
    a.set_ylim(0, 1)
    a.set_yticks([0, 0.25, 0.5, 0.75, 1])
    a.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    a.set_xlabel("Round of learning (64 orders each)")
    a.set_ylabel("Orders with the spoof's signature")
    a.set_title("Does it learn to spoof?")
    a.legend(fontsize=7.5, loc="upper left")
    b.axhline(0, color=AXIS, linewidth=1)
    b.set_xlabel("Round of learning")
    b.set_ylabel("Price achieved vs arrival mid (ticks per lot)")
    b.set_title("What it earns (before fines)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
