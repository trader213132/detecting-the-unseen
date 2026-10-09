"""Part 2: what kind of teaching makes manipulation detectable?

    python run_teaching.py                       (everything, roughly 30 minutes)
    python run_teaching.py --only principle      (or markets, accounts, examples, reversal)

The main experiment found that detectors which only learn what normal trading looks
like cannot tell a spoof from an honest large order of the same size. This script gives
the detectors more and more prior knowledge, a "ladder of teaching":

  0. NOTHING      unusualness only (PCA, Isolation Forest, LSTM...)     main experiment
  1. EXAMPLES     a classifier shown k labelled spoof orders             --only examples
  2. A PATTERN    the hand-written rule "large order cancelled quickly"  main experiment
  3. A PRINCIPLE  the legal definition of the offence, and no examples   --only principle

The principle detector reads which ACCOUNT placed each order, as a regulator can. Its
control is an untaught Isolation Forest given exactly the same account data: if that
does as well, the account data did the work, not the principle.

Every rung is also tested on the hardest honest case there is (--only reversal): a trader
who rests a large order, changes their mind as if on news, withdraws it and trades the
other way. Its footprint matches a spoof; only the intent differs.

Stress tests (--only markets, --only accounts): the four alternative markets from
run_extensions.py, and different ways accounts can be organised (how many traders share
an account; a spoofer hiding inside a broker's shared "omnibus" account; window length).
Attack (--only evasion): a spoofer who places the wall from one account and the small
order from another, against three versions of the principle detector.

Results: results/teaching_*.csv and results/teaching.md
"""
import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src import accounts as A
from src.evaluate import auc, bootstrap_auc_ci, bootstrap_ci, paired_difference
from src.experiment import FULL, dataset_specs
from src.isolation_forest import IsolationForest
from src.market import run_session

ROOT = Path(__file__).parent
DATA, RESULTS = ROOT / "data" / "accounts", ROOT / "results"
SMALL = {"train": 20, "val": 8, "normal": 12, "spoof": 25, "layer": 20, "control": 12}
MARKETS = {
    "fewer book-readers": {"reactive_share": 0.25, "mm_react_shift": 1.5},
    "more book-readers": {"reactive_share": 0.75, "mm_react_shift": 4.5},
    "thinner book": {"arrival_rate": 1.0, "mm_size": 2},
    "impatient traders": {"mean_patience": 20.0},
}
PRINCIPLE, UNTAUGHT = "Principle (accounts)", "Untaught IForest (accounts)"
TARGET = 0.01          # alert threshold: 1% of normal windows contain any alert


# --- Data -----------------------------------------------------------------------
def with_reversals(specs, n, sizes, seed_base=0):
    """Add the two honest change-of-mind cases, each with its own seeds:
    reversal (cancel, then trade the other way) and withdrawal (cancel, trade nothing)."""
    for m in sizes:
        specs[f"reversal_calm_{m}"] = [(seed_base + 40_000 + 100 * m + i, "calm", [("reversal", m)] * 2)
                                       for i in range(n)]
        specs[f"withdrawal_calm_{m}"] = [(seed_base + 45_000 + 100 * m + i, "calm", [("withdrawal", m)] * 2)
                                         for i in range(n)]
    return specs


def simulate_accounts(seed, regime, specials, overrides=None, window=A.WINDOW, owners=None):
    s = run_session(seed, regime, specials, overrides)
    rows = A.account_rows(s, window=window, owners=owners)
    rows["X"] = rows["X"].astype(np.int16)                      # lot counts: small whole numbers
    episodes = [{"kind": ep["kind"], "size_mult": ep["size_mult"], "start": ep["start"],
                 "account": ep["account"], "small_filled": bool(ep.get("small_filled"))} for ep in s.episodes]
    return {"seed": seed, "rows": rows, "episodes": episodes}


def load(name, spec, cache, overrides=None, window=A.WINDOW, fresh=False, log=print, owners=None):
    path = cache / f"{name}.pkl"
    if path.exists() and not fresh:
        return pickle.loads(path.read_bytes())
    log(f"  simulating {cache.name}/{name} ({len(spec)} sessions)")
    out = [simulate_accounts(*s, overrides=overrides, window=window, owners=owners) for s in spec]
    cache.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(out))
    return out


# --- Detectors ------------------------------------------------------------------
class UntaughtAccounts:
    """Isolation Forest on the account rows: learns what normal accounts' windows look like."""

    def fit(self, sessions, n=20_000, seed=0):
        X = np.concatenate([A.generic_features(s["rows"]["X"].astype(float)) for s in sessions])
        pick = np.random.default_rng(seed).choice(len(X), size=min(n, len(X)), replace=False)
        self.forest = IsolationForest(n_trees=200, sample_size=256, seed=seed).fit(X[pick])
        return self

    def score(self, X):
        # Many rows are identical (one small order, nothing else), so score each distinct row once.
        uniq, inverse = np.unique(X, axis=0, return_inverse=True)
        return self.forest.score(A.generic_features(uniq.astype(float)))[inverse.ravel()]


def principle(rows):
    return A.principle_score(rows["X"].astype(float))


def pairs(rows):
    return A.pair_score(rows, rows["X"].astype(float))


# --- One complete evaluation ----------------------------------------------------
def run_setting(label, specs, cache, overrides=None, window=A.WINDOW, fresh=False, log=print, untaught=True,
                detectors=None, owners=None):
    """Fit (untaught only), set thresholds on normal validation sessions, score every test set.
    Returns (episodes, normals): one row per (detector, episode) and per (detector, normal session)."""
    get = lambda name: load(name, specs[name], cache, overrides, window, fresh, log, owners)
    if detectors is None:
        detectors = {PRINCIPLE: principle}
        if untaught:
            forest = UntaughtAccounts().fit(get("train_calm"))
            detectors[UNTAUGHT] = lambda rows: forest.score(rows["X"])
    span = window
    taus = {}
    for det, score in detectors.items():
        val = np.concatenate([A.window_max(s["rows"], score(s["rows"])) for s in get("val_calm")])
        taus[det] = float(np.quantile(val, 1 - TARGET))
    episodes, normals = [], []
    for name in specs:
        if name.startswith(("train_", "val_", "honest")):
            continue
        sessions = get(name)
        for i, s in enumerate(sessions):
            for det, score in detectors.items():
                sc = score(s["rows"])
                tau = taus[det]
                if name.startswith("normal_"):
                    w = A.window_max(s["rows"], sc)
                    normals.append({"setting": label, "detector": det, "regime": name.split("_")[1], "session": i,
                                    "threshold": tau, "fpr": float(np.mean(w > tau)),
                                    "span_max": A.span_maxes(s["rows"], sc, span) / max(tau, 1e-9)})
                    continue
                for j, ep in enumerate(s["episodes"]):
                    value = A.episode_score(s["rows"], sc, ep["start"], ep["account"], span)
                    episodes.append({"setting": label, "detector": det, "test": name.rsplit("_", 1)[0],
                                     "size_mult": ep["size_mult"], "session": i, "episode": j,
                                     "score": value, "ratio": value / max(tau, 1e-9), "hit": value > tau,
                                     "small_filled": ep["small_filled"], "threshold": tau})
    return pd.DataFrame(episodes), pd.DataFrame(normals)


def summarise(eps, normals):
    """Catch / flag rates with intervals, false alarms, and threshold-free AUCs."""
    rows = []
    for (setting, det), d in eps.groupby(["setting", "detector"]):
        nrm = normals[(normals.setting == setting) & (normals.detector == det)]
        span_calm = np.concatenate(nrm[nrm.regime == "calm"].span_max.to_list()) if len(nrm) else np.array([])
        base = {"setting": setting, "detector": det, "threshold": float(d.threshold.iloc[0])}
        for regime in ("calm", "volatile"):
            q = nrm[nrm.regime == regime]
            if len(q):
                low, high = bootstrap_ci(q.fpr)
                rows.append({**base, "test": f"normal_{regime}", "metric": "false_alarm_windows",
                             "size_mult": np.nan, "value": q.fpr.mean(), "ci_low": low, "ci_high": high, "n": len(q)})
        for (test, m), q in d.groupby(["test", "size_mult"]):
            metric = "flag_rate" if test.startswith(("control", "reversal", "withdrawal")) else "catch_rate"
            low, high = bootstrap_ci(q.hit)
            rows.append({**base, "test": test, "metric": metric, "size_mult": m, "value": q.hit.mean(),
                         "ci_low": low, "ci_high": high, "n": len(q)})
            if metric == "catch_rate":
                ok = q[q.small_filled]
                if len(ok):
                    rows.append({**base, "test": test, "metric": "catch_rate_when_it_paid", "size_mult": m,
                                 "value": ok.hit.mean(), "ci_low": np.nan, "ci_high": np.nan, "n": len(ok)})
            against = {"genuine": d[(d.test == "control_calm") & (d.size_mult == m)].ratio.to_numpy(),
                       "reversal": d[(d.test == "reversal_calm") & (d.size_mult == m)].ratio.to_numpy(),
                       "withdrawal": d[(d.test == "withdrawal_calm") & (d.size_mult == m)].ratio.to_numpy(),
                       "normal": span_calm}
            if metric == "catch_rate":
                for name, neg in against.items():
                    if len(neg) and len(q):
                        low, high = bootstrap_auc_ci(q.ratio.to_numpy(), neg)
                        rows.append({**base, "test": test, "metric": f"auc_vs_{name}", "size_mult": m,
                                     "value": auc(q.ratio.to_numpy(), neg), "ci_low": low, "ci_high": high,
                                     "n": len(q)})
    return pd.DataFrame(rows)


def paired_with_main(eps):
    """Principle vs the main experiment's detectors, judged on the SAME episodes (same seeds)."""
    main = pd.read_csv(RESULTS / "episodes.csv")
    main = main[main.condition == "calm-trained"]
    mine = eps[(eps.setting == "main") & (eps.detector == PRINCIPLE)]
    rows = []
    for other in ["Rule", "PCA (informed)", "IForest (generic)", "LSTM-AE (generic)"]:
        for test in ("spoof_calm", "layer_calm", "control_calm"):
            for m in (4, 8, 16):
                a = mine[(mine.test == test) & (mine.size_mult == m)].set_index(["session", "episode"]).hit
                b = main[(main.detector == other) & (main.test == test) & (main.size_mult == m)] \
                    .set_index(["session", "episode"]).hit
                both = a.to_frame("a").join(b.rename("b"), how="inner")
                if len(both) == 0:
                    continue
                diff, low, high, p = paired_difference(both.a.to_numpy(), both.b.astype(bool).to_numpy())
                rows.append({"a": PRINCIPLE, "b": other, "test": test, "size_mult": m, "n": len(both),
                             "rate_a": both.a.mean(), "rate_b": both.b.astype(bool).mean(),
                             "difference": diff, "ci_low": low, "ci_high": high, "p_value": p})
    return pd.DataFrame(rows)


# --- Sections -------------------------------------------------------------------
def run_principle(fresh):
    print("== Principle vs untaught, on account data (main market, same seeds as the main experiment)")
    specs = with_reversals(dataset_specs(FULL), 30, (1, 2, 4, 8, 16))
    specs = {k: v for k, v in specs.items() if not k.startswith(("honest", "train_volatile", "val_volatile"))}
    eps, normals = run_setting("main", specs, DATA / "main", fresh=fresh)
    eps.to_csv(RESULTS / "teaching_episodes.csv", index=False)
    summary = summarise(eps, normals)
    summary.to_csv(RESULTS / "teaching_principle.csv", index=False)
    paired = paired_with_main(eps)
    paired.to_csv(RESULTS / "teaching_paired.csv", index=False)
    return summary, paired


def run_markets(fresh):
    frames = []
    for i, (name, overrides) in enumerate(MARKETS.items()):
        print(f"== Market: {name}")
        specs = with_reversals(dataset_specs(SMALL, sizes=(8, 16), regimes=("calm",), seed_base=100_000 * (i + 1)),
                               12, (8, 16), seed_base=100_000 * (i + 1))
        specs = {k: v for k, v in specs.items() if not k.startswith("honest")}
        eps, normals = run_setting(name, specs, DATA / ("market_" + name.replace(" ", "_")), overrides, fresh=fresh)
        frames.append(summarise(eps, normals))
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(RESULTS / "teaching_markets.csv", index=False)
    return out


def run_accounts(fresh):
    """How accounts are organised changes nothing in the market, only who did what."""
    base = with_reversals(dataset_specs(SMALL, sizes=(8, 16), regimes=("calm",), seed_base=1_200_000),
                          12, (8, 16), seed_base=1_200_000)
    base = {k: v for k, v in base.items() if not k.startswith("honest")}
    settings = [(f"pool{n}", f"{n} accounts per trader type", {"accounts_per_kind": n}, A.WINDOW)
                for n in (10, 25, 50, 200, 800)]
    settings += [(f"omnibus{round(s * 100)}", f"spoofer inside an omnibus account carrying {s:.0%} of all orders",
                  {"omnibus_share": s}, A.WINDOW) for s in (0.01, 0.05, 0.2)]
    settings += [(f"window{w}", f"{w}-step windows", None, w) for w in (20, 80, 160)]
    frames = []
    for tag, label, overrides, window in settings:
        print(f"== Accounts: {label}")
        eps, normals = run_setting(label, base, DATA / ("accounts_" + tag), overrides, window, fresh, untaught=False)
        frames.append(summarise(eps, normals))
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(RESULTS / "teaching_accounts.csv", index=False)
    return out


def run_evasion(fresh):
    """An evasive spoofer places the wall from one account and the small order from another."""
    base = with_reversals(dataset_specs(SMALL, sizes=(8, 16), regimes=("calm",), seed_base=1_300_000),
                          12, (8, 16), seed_base=1_300_000)
    base = {k: v for k, v in base.items() if not k.startswith("honest")}
    two = {"spoofer_accounts": 2}
    settings = [("evade1", "two accounts; checked one account at a time", {PRINCIPLE: principle}, None),
                ("evade2", "two accounts; regulator links accounts to their owner", {PRINCIPLE: principle}, {4001: 4000}),
                ("evade3", "two accounts; every pair of accounts checked, no links", {"Principle (any two accounts)": pairs}, None)]
    frames = []
    for tag, label, detectors, owners in settings:
        print(f"== Evasion: {label}")
        cache = DATA / ("evasion_linked" if owners else "evasion")
        eps, normals = run_setting(label, base, cache, two, fresh=fresh, detectors=detectors, owners=owners)
        frames.append(summarise(eps, normals))
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(RESULTS / "teaching_evasion.csv", index=False)
    return out


def run_reversal(fresh):
    """Every rung of the main experiment, on the honest change-of-mind episodes."""
    from src.experiment import evaluate, load_or_simulate, make_detectors, rate_metrics
    print("== Reversal: the main experiment's detectors on honest changes of mind")
    specs = dataset_specs(FULL)
    honest = with_reversals({}, 30, (1, 2, 4, 8, 16))
    rev = {f"control_{name}": spec for name, spec in honest.items()}     # "control_" so evaluate() scores them
    data = load_or_simulate({k: specs[k] for k in ("train_calm", "val_calm", "normal_calm")}, ROOT / "data")
    data.update(load_or_simulate(rev, ROOT / "data" / "reversal", fresh))
    ev = evaluate(data, ["train_calm"], ["val_calm"], "calm-trained", detectors=make_detectors())
    out = pd.DataFrame(rate_metrics(ev))
    out = out[out.test.isin(["control_reversal_calm", "control_withdrawal_calm"])]
    out = out.assign(test=out.test.str.replace("control_", "", regex=False))
    out.to_csv(RESULTS / "teaching_reversal_main.csv", index=False)
    return out


def run_examples(fresh):
    """Rung 1: a classifier shown k labelled spoof orders (logistic regression on the same
    four order features the untaught order-level detector used)."""
    from src.orders import ORDER_FEATURES
    cache = ROOT / "data" / "orders"
    if not (cache / "train_calm.pkl").exists():
        raise SystemExit("Run `python run_extensions.py --only orders` first (it simulates the order tables).")
    from src.orders import mark_special_orders, order_table
    for name, spec in with_reversals({}, 12, (8, 16), seed_base=700_000).items():   # honest changes of mind
        path = cache / f"{name}.pkl"
        if fresh or not path.exists():
            print(f"  simulating orders/{name}")
            sessions = [run_session(*sp) for sp in spec]
            path.write_bytes(pickle.dumps([mark_special_orders(order_table(x), x) for x in sessions]))
    tables = {p.stem: pickle.loads(p.read_bytes()) for p in cache.glob("*.pkl")}
    stack = lambda name, keep=lambda i: True: pd.concat(
        [t.assign(session=i) for i, t in enumerate(tables[name]) if keep(i)], ignore_index=True)
    cols = ORDER_FEATURES
    train_neg = stack("train_calm")
    mean, std = train_neg[cols].mean(), train_neg[cols].std().replace(0, 1)
    z = lambda t: ((t[cols] - mean) / std).to_numpy()
    rng = np.random.default_rng(0)
    neg = z(train_neg)[rng.choice(len(train_neg), 20_000, replace=False)]
    val_neg = z(stack("val_calm"))
    normal = stack("normal_calm")
    # Labelled examples come from the first half of the spoof sessions; testing uses the second half.
    pool = pd.concat([stack(f"spoof_calm_{m}", lambda i: i < 12) for m in (8, 16)]).query("role == 'spoof wall'")
    test_walls = {m: stack(f"spoof_calm_{m}", lambda i: i >= 12).query("role == 'spoof wall'") for m in (8, 16)}
    layered = {m: stack(f"layer_calm_{m}").query("role == 'layered piece'") for m in (8, 16)}
    # Honest large orders: the first half of the control sessions can be shown as labelled honest
    # examples (second variant); testing always uses the second half.
    honest_pool = pd.concat([stack(f"control_calm_{m}", lambda i: i < 6) for m in (8, 16)]).query("role == 'genuine large'")
    genuine = {m: stack(f"control_calm_{m}", lambda i: i >= 6).query("role == 'genuine large'") for m in (8, 16)}
    reversal = {m: stack(f"reversal_calm_{m}").query("role == 'honest reversal'") for m in (8, 16)}
    withdrawal = {m: stack(f"withdrawal_calm_{m}").query("role == 'honest withdrawal'") for m in (8, 16)}
    P, H = z(pool), z(honest_pool)
    rows = []
    runs = [(variant, k, draw) for variant in ("spoofs only", "spoofs and honest large orders")
            for k in (1, 2, 5, 10, 20, 40) for draw in range(30)]
    for variant, k, draw in runs:
        spoofs = P[rng.choice(len(P), size=k, replace=False)]
        honest = H[rng.choice(len(H), size=min(k, len(H)), replace=False)] if variant != "spoofs only" else H[:0]
        w = logistic_fit(spoofs, neg, honest)
        f = lambda X: X @ w[:-1] + w[-1]
        tau = float(np.quantile(f(val_neg), 0.999))          # 1 normal order in 1,000 alerts
        for m in (8, 16):
            s_wall, s_gen = f(z(test_walls[m])), f(z(genuine[m]))
            pieces = layered[m]
            s_layer = (pd.Series(f(z(pieces)), index=pieces.index)
                       .groupby([pieces.session.to_numpy(), pieces.start.to_numpy()]).max().to_numpy())
            rows.append({"variant": variant, "k": k, "draw": draw, "size_mult": m, "threshold": tau,
                         "spoof_walls_caught": np.mean(s_wall > tau), "layered_caught": np.mean(s_layer > tau),
                         "genuine_flagged": np.mean(s_gen > tau),
                         "reversal_flagged": np.mean(f(z(reversal[m])) > tau),
                         "withdrawal_flagged": np.mean(f(z(withdrawal[m])) > tau),
                         "normal_orders_flagged": np.mean(f(z(normal)) > tau),
                         "auc_spoof_vs_genuine": auc(s_wall, s_gen), "auc_layered_vs_genuine": auc(s_layer, s_gen)})
        if draw == 29:
            print(f"  examples ({variant}): k={k} done")
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "teaching_examples.csv", index=False)
    return out


def logistic_fit(spoofs, normal, honest, l2=1e-2, steps=400, lr=0.5):
    """Plain logistic regression by gradient descent. Each group counts equally however many
    rows it has: the labelled spoofs (half the weight), the normal orders, and the labelled
    honest large orders if any (sharing the other half). Returns weights + bias."""
    X = np.vstack([spoofs, normal, honest])
    y = np.r_[np.ones(len(spoofs)), np.zeros(len(normal) + len(honest))]
    share = 0.25 if len(honest) else 0.5
    weight = np.r_[np.full(len(spoofs), 0.5 / len(spoofs)), np.full(len(normal), share / len(normal)),
                   np.full(len(honest), 0.25 / max(len(honest), 1))]
    Xb = np.hstack([X, np.ones((len(X), 1))])
    w = np.zeros(Xb.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-np.clip(Xb @ w, -30, 30)))
        grad = Xb.T @ (weight * (p - y)) + l2 * np.r_[w[:-1], 0]
        w -= lr * grad
    return w


# --- Report ---------------------------------------------------------------------
def pct(x):
    return "" if pd.isna(x) else f"{x:.0%}"


def write_report():
    L = ["# Part 2: what kind of teaching makes manipulation detectable?", "",
         "All numbers come from simulated markets. Brackets are 95% bootstrap intervals. Alert thresholds: "
         "1% of normal 40-step windows contain any alert (account detectors), which is stricter than the "
         "main experiment's 1% of bars.", ""]
    p = RESULTS / "teaching_principle.csv"
    if p.exists():
        s = pd.read_csv(p)

        def get(det, test, metric, m=None):
            q = s[(s.detector == det) & (s.test == test) & (s.metric == metric)]
            if m is not None:
                q = q[q.size_mult == m]
            return q.iloc[0] if len(q) else None

        L += ["## The principle detector vs an untaught detector on the same account data", "",
              "| Detector | Test | 1× | 2× | 4× | 8× | 16× |", "|---|---|---|---|---|---|---|"]
        for det in (PRINCIPLE, UNTAUGHT):
            for test, metric, label in [("spoof_calm", "catch_rate", "Spoofs caught"),
                                        ("layer_calm", "catch_rate", "Layered spoofs caught"),
                                        ("spoof_volatile", "catch_rate", "Spoofs caught, volatile market"),
                                        ("control_calm", "flag_rate", "Genuine large orders flagged"),
                                        ("withdrawal_calm", "flag_rate", "Honest quick withdrawals flagged"),
                                        ("reversal_calm", "flag_rate", "Honest changes of mind flagged")]:
                cells = []
                for m in (1, 2, 4, 8, 16):
                    r = get(det, test, metric, m)
                    cells.append("" if r is None else f"{r.value:.0%} ({r.ci_low:.0%}–{r.ci_high:.0%})")
                L.append(f"| {det} | {label} | " + " | ".join(cells) + " |")
        L += ["", "| Detector | False-alarm windows, calm | False-alarm windows, volatile (never trained on it) | Threshold |",
              "|---|---|---|---|"]
        for det in (PRINCIPLE, UNTAUGHT):
            c, v = get(det, "normal_calm", "false_alarm_windows"), get(det, "normal_volatile", "false_alarm_windows")
            L.append(f"| {det} | {c.value:.1%} | {v.value:.1%} | {c.threshold:.3g} |")
        L += ["", "AUC (threshold-free), 16×:", "", "| Detector | Spoof vs genuine | Layered vs genuine | Spoof vs normal | Spoof vs honest change of mind |",
              "|---|---|---|---|---|"]
        for det in (PRINCIPLE, UNTAUGHT):
            a = [get(det, t, f"auc_vs_{n}", 16) for t, n in [("spoof_calm", "genuine"), ("layer_calm", "genuine"),
                                                              ("spoof_calm", "normal"), ("spoof_calm", "reversal")]]
            L.append(f"| {det} | " + " | ".join("" if r is None else f"{r.value:.2f} ({r.ci_low:.2f}–{r.ci_high:.2f})"
                                                for r in a) + " |")
    p = RESULTS / "teaching_paired.csv"
    if p.exists():
        d = pd.read_csv(p)
        L += ["", "## Same episodes, compared (paired bootstrap)", "",
              "| A | B | Test | Size | A | B | A − B (95% CI) | p |", "|---|---|---|---|---|---|---|---|"]
        for r in d.itertuples():
            L.append(f"| {r.a} | {r.b} | {r.test} | {r.size_mult}× | {r.rate_a:.0%} | {r.rate_b:.0%} | "
                     f"{r.difference * 100:+.0f} pts ({r.ci_low * 100:+.0f} to {r.ci_high * 100:+.0f}) | {r.p_value:.3f} |")
    p = RESULTS / "teaching_reversal_main.csv"
    if p.exists():
        d = pd.read_csv(p)
        L += ["", "## The hardest honest case, for every rung of the main experiment", "",
              "Share of honest episodes flagged (same thresholds as the main experiment). Withdrawal: a large order "
              "cancelled after 5-25 steps, nothing traded. Reversal: the same, then a small trade the other way.", "",
              "| Detector | Case | 1× | 2× | 4× | 8× | 16× |", "|---|---|---|---|---|---|---|"]
        d = d[d.metric == "flag_rate"]
        for (det, test), q in d.groupby(["detector", "test"], sort=False):
            q = q.set_index("size_mult").value
            L.append(f"| {det} | {test.split('_')[0]} | " + " | ".join(pct(q.get(m)) for m in (1, 2, 4, 8, 16)) + " |")
    p = RESULTS / "teaching_examples.csv"
    if p.exists():
        d = pd.read_csv(p)
        L += ["", "## Rung 1: taught by examples", "",
              "Logistic regression on the four order features, shown k labelled spoof walls (single-wall, 8× and 16×) "
              "and 20,000 normal orders; in the second variant also k labelled honest large orders. 30 random draws "
              "of examples per k: median (10th–90th percentile). Threshold: 1 normal order in 1,000. Test sessions "
              "are never the ones examples came from.", "",
              "| Shown | k examples | Size | Spoof walls caught | Layered caught | Genuine flagged | Quick withdrawals flagged | Changes of mind flagged | AUC spoof vs genuine |",
              "|---|---|---|---|---|---|---|---|---|"]
        for (v, k, m), q in d.groupby(["variant", "k", "size_mult"], sort=False):
            f = lambda c: f"{q[c].median():.0%} ({q[c].quantile(.1):.0%}–{q[c].quantile(.9):.0%})"
            L.append(f"| {v} | {k} | {m}× | {f('spoof_walls_caught')} | {f('layered_caught')} | {f('genuine_flagged')} | "
                     f"{f('withdrawal_flagged')} | {f('reversal_flagged')} | "
                     f"{q.auc_spoof_vs_genuine.median():.2f} |")
    for name, title in [("teaching_markets.csv", "Stress test: four alternative markets"),
                        ("teaching_accounts.csv", "Stress test: how accounts are organised"),
                        ("teaching_evasion.csv", "Attack: a spoofer who uses two accounts")]:
        p = RESULTS / name
        if not p.exists():
            continue
        d = pd.read_csv(p)
        L += ["", f"## {title}", "",
              "| Setting | Detector | Spoofs 8× | Spoofs 16× | Layered 8× | Layered 16× | Genuine flagged 16× | "
              "Quick withdrawals flagged 16× | Changes of mind flagged 16× | False-alarm windows |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for (setting, det), q in d.groupby(["setting", "detector"], sort=False):
            v = lambda t, m=None, metric=None: q[(q.test == t) & ((q.size_mult == m) if m else True) &
                                                ((q.metric == metric) if metric else True)].value
            g = lambda t, m: pct(v(t, m).iloc[0]) if len(v(t, m)) else ""
            fa = v("normal_calm", metric="false_alarm_windows")
            L.append(f"| {setting} | {det} | {g('spoof_calm', 8)} | {g('spoof_calm', 16)} | {g('layer_calm', 8)} | "
                     f"{g('layer_calm', 16)} | {g('control_calm', 16)} | {g('withdrawal_calm', 16)} | {g('reversal_calm', 16)} | "
                     f"{fa.iloc[0]:.1%} |" if len(fa) else "")
    (RESULTS / "teaching.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def plot_ladder():
    """results/figures/fig7_ladder_of_teaching.png, from Part 1's and Part 2's results files."""
    from src.plots import ladder_of_teaching
    m = pd.read_csv(RESULTS / "metrics.csv")
    m = m[(m.condition == "calm-trained") & (m.size_mult == 16)]
    main = lambda det, test: tuple(m[(m.detector == det) & (m.test == test)][["value", "ci_low", "ci_high"]].iloc[0])
    rev = pd.read_csv(RESULTS / "teaching_reversal_main.csv")
    rev = rev[(rev.metric == "flag_rate") & (rev.size_mult == 16)]
    reversal = lambda det, case="reversal_calm": tuple(
        rev[(rev.detector == det) & (rev.test == case)][["value", "ci_low", "ci_high"]].iloc[0])
    pr = pd.read_csv(RESULTS / "teaching_principle.csv")
    pr = pr[(pr.setting == "main") & (pr.detector == PRINCIPLE) & (pr.size_mult == 16)]
    principle_cell = lambda test, metric: tuple(pr[(pr.test == test) & (pr.metric == metric)][["value", "ci_low", "ci_high"]].iloc[0])
    ex = pd.read_csv(RESULTS / "teaching_examples.csv")
    ex = ex[(ex.variant == "spoofs and honest large orders") & (ex.k == 10) & (ex.size_mult == 16)]
    example = lambda c: (ex[c].median(), ex[c].quantile(0.1), ex[c].quantile(0.9))
    lstm = "LSTM-AE (generic)"
    rows = [("0  Nothing\n(LSTM autoencoder)", [main(lstm, "spoof_calm"), main(lstm, "layer_calm"), main(lstm, "control_calm"),
                                                reversal(lstm, "withdrawal_calm"), reversal(lstm)]),
            ("1  Examples\n(10 spoofs + 10 honest)", [example("spoof_walls_caught"), example("layered_caught"),
                                                      example("genuine_flagged"), example("withdrawal_flagged"),
                                                      example("reversal_flagged")]),
            ("2  A pattern\n(the rule)", [main("Rule", "spoof_calm"), main("Rule", "layer_calm"), main("Rule", "control_calm"),
                                          reversal("Rule", "withdrawal_calm"), reversal("Rule")]),
            ("3  A principle\n(the legal definition)", [principle_cell("spoof_calm", "catch_rate"), principle_cell("layer_calm", "catch_rate"),
                                                        principle_cell("control_calm", "flag_rate"),
                                                        principle_cell("withdrawal_calm", "flag_rate"),
                                                        principle_cell("reversal_calm", "flag_rate")])]
    ladder_of_teaching(rows, RESULTS / "figures" / "fig7_ladder_of_teaching.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--only", choices=["principle", "reversal", "examples", "markets", "accounts", "evasion"])
    args = parser.parse_args()
    sections = {"principle": run_principle, "reversal": run_reversal, "examples": run_examples,
                "markets": run_markets, "accounts": run_accounts, "evasion": run_evasion}
    for name, run in sections.items():
        if args.only in (None, name):
            run(args.fresh)
    write_report()
    if all((RESULTS / f).exists() for f in ("teaching_principle.csv", "teaching_reversal_main.csv", "teaching_examples.csv")):
        plot_ladder()
    sys.stdout.reconfigure(encoding="utf-8")         # the report uses − and × signs
    print((RESULTS / "teaching.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
