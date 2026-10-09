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
