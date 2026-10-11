"""Write the research report from the results files.

    python build_report.py          (after run_experiments.py, run_extensions.py and run_teaching.py)

Every number and table in the report is read from results/*.csv here, never typed by hand,
so the report always matches the experiments. Output:
    docs/report.html   the report as a web page (linked from the website)
    docs/report.pdf    the same report as a PDF, printed with Google Chrome if it is installed
"""
import html
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
RESULTS, DOCS = ROOT / "results", ROOT / "docs"
FIGS = DOCS / "report-figures"
CHROME = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
          Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")]

UNTAUGHT = ["PCA (generic)", "IForest (generic)", "Seq-PCA (generic)", "LSTM-AE (generic)"]
NAMES = {"Rule": "Rule", "PCA (generic)": "PCA", "PCA (informed)": "PCA, spoof-informed",
         "IForest (generic)": "Isolation Forest", "IForest (informed)": "Isolation Forest, spoof-informed",
         "Seq-PCA (generic)": "Sequence PCA", "LSTM-AE (generic)": "LSTM autoencoder"}
DETECTORS = list(NAMES)
PRINCIPLE, UNTAUGHT_ACC = "Principle (accounts)", "Untaught IForest (accounts)"


# --- Reading results ------------------------------------------------------------
m = pd.read_csv(RESULTS / "metrics.csv")
a = pd.read_csv(RESULTS / "auc.csv")
impact = pd.read_csv(RESULTS / "impact.csv")
paired = pd.read_csv(RESULTS / "paired.csv")
shuffle = pd.read_csv(RESULTS / "shuffle.csv")
sens = pd.read_csv(RESULTS / "sensitivity.csv")
res = pd.read_csv(RESULTS / "resolution.csv")
orders = pd.read_csv(RESULTS / "orders.csv")
tp = pd.read_csv(RESULTS / "teaching_principle.csv")
tpair = pd.read_csv(RESULTS / "teaching_paired.csv")
trev = pd.read_csv(RESULTS / "teaching_reversal_main.csv")
tex = pd.read_csv(RESULTS / "teaching_examples.csv")
tmk = pd.read_csv(RESULTS / "teaching_markets.csv")
tac = pd.read_csv(RESULTS / "teaching_accounts.csv")
tev = pd.read_csv(RESULTS / "teaching_evasion.csv")
price = pd.read_csv(RESULTS / "evasion_cost.csv")
price_honest = pd.read_csv(RESULTS / "evasion_cost_honest.csv")


def row(df, **kw):
    q = df
    for k, v in kw.items():
        q = q[q[k] == v]
    if len(q) == 0:
        raise KeyError(kw)
    return q.iloc[0]


def metric(det, test, metric_name, size=None, cond="calm-trained"):
    q = m[(m.condition == cond) & (m.detector == det) & (m.test == test) & (m.metric == metric_name)]
    if size is not None:
        q = q[q.size_mult == size]
    return q.iloc[0]


def rate(det, test, size, cond="calm-trained"):
    return metric(det, test, "flag_rate" if test.startswith("control") else "catch_rate", size, cond).value


def auc(det, test, against, size, cond="calm-trained"):
    return row(a, condition=cond, detector=det, test=test, against=against, size_mult=size)


def princ(test, metric_name, size=None, setting="main", det=PRINCIPLE, df=tp):
    q = df[(df.setting == setting) & (df.detector == det) & (df.test == test) & (df.metric == metric_name)]
    if size is not None:
        q = q[q.size_mult == size]
    return q.iloc[0]


def pct(x, d=0):
    return "n/a" if pd.isna(x) else f"{x * 100:.{d}f}%"


def ci(r, d=0, fmt=pct):
    return f"{fmt(r.ci_low, d)} to {fmt(r.ci_high, d)}" if fmt is pct else f"{r.ci_low:.2f} to {r.ci_high:.2f}"


def dec(x):
    return f"{x:.2f}"


def table(head, rows, caption, num_from=1):
    h = "".join(f"<th{' class=num' if i >= num_from else ''}>{html.escape(c)}</th>" for i, c in enumerate(head))
    body = "".join("<tr>" + "".join(f"<td{' class=num' if i >= num_from else ''}>{c}</td>" for i, c in enumerate(r)) + "</tr>"
                   for r in rows)
    return f"<figure class=tbl><figcaption>{caption}</figcaption><table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></figure>"


def fig(name, caption):
    FIGS.mkdir(parents=True, exist_ok=True)
    shutil.copy(RESULTS / "figures" / name, FIGS / name)
    return f"<figure class=fig><img src='report-figures/{name}' alt=''><figcaption>{caption}</figcaption></figure>"


# --- Numbers used in the text ------------------------------------------------------
im = lambda kind, size: row(impact, spoof=kind, size_mult=size)
fill8, fill16, layfill8 = im("single wall", 8), im("single wall", 16), im("layered", 8)
lstm_auc16 = auc("LSTM-AE (generic)", "spoof_calm", "genuine", 16)
untaught_auc16 = [auc(d, "spoof_calm", "genuine", 16).auc for d in UNTAUGHT]
vol_fpr = [metric(d, "normal_volatile", "false_alarm_rate").value for d in DETECTORS if d != "Rule"]
mix_fpr = [metric(d, "normal_volatile", "false_alarm_rate", cond="mixed-trained").value for d in DETECTORS if d != "Rule"]
chance_calm = metric("Rule", "normal_calm", "chance_catch_rate").value
rule_thr = metric("Rule", "spoof_calm", "catch_rate", 16).threshold
ord16 = row(orders, variant="all four features", size_mult=16)
ord_nosize = row(orders, variant="without size", size_mult=16)
pr = lambda test, met, size=None: princ(test, met, size)
pr_vs_rule = row(tpair, b="Rule", test="layer_calm", size_mult=16)
rev = lambda det, test="reversal_calm", size=16: row(trev[trev.metric == "flag_rate"], detector=det, test=test, size_mult=size).value
exq = lambda variant, size: tex[(tex.variant == variant) & (tex.k == 10) & (tex.size_mult == size)]
ex_both16, ex_only16, ex_both8 = exq("spoofs and honest large orders", 16), exq("spoofs only", 16), exq("spoofs and honest large orders", 8)
evs = lambda key, test, size, met: tev[(tev.setting.str.contains(key)) & (tev.test == test) & (tev.size_mult == size) & (tev.metric == met)].iloc[0]
omni20 = "spoofer inside an omnibus account carrying 20% of all orders"
mk_spoof16 = tmk[(tmk.detector == PRINCIPLE) & (tmk.test == "spoof_calm") & (tmk.size_mult == 16) & (tmk.metric == "catch_rate")].value
mk_layer16 = tmk[(tmk.detector == PRINCIPLE) & (tmk.test == "layer_calm") & (tmk.size_mult == 16) & (tmk.metric == "catch_rate")].value
n_sessions = sum(len(__import__("pickle").loads(p.read_bytes())) for p in (ROOT / "data").glob("*.pkl"))


# --- Tables ---------------------------------------------------------------------
t_impact = table(
    ["Spoof", "Size", "Fill chance, with wall", "Fill chance, honest twin", "Extra fill chance (95% CI)", "Price shift, ticks"],
    [[r.spoof, f"{r.size_mult}×", pct(r.fill_rate_wall), pct(r.fill_rate_honest),
      f"{r.fill_gain * 100:+.0f} pts ({r.fill_gain_ci_low * 100:+.0f} to {r.fill_gain_ci_high * 100:+.0f})",
      f"{r.shift_vs_honest:+.2f}"] for r in impact.itertuples()],
    "Table 1. Does spoofing work? Each spoof episode compared with its honest twin: the same session, seed and "
    "schedule, but with no wall. Calm market.", num_from=1)

t_catch = table(
    ["Detector", "Spoofs 4×", "Spoofs 8×", "Spoofs 16×", "Layered 16×", "Honest large 8×", "Honest large 16×"],
    [[NAMES[d]] + [pct(rate(d, "spoof_calm", s)) for s in (4, 8, 16)] + [pct(rate(d, "layer_calm", 16)),
                                                                       pct(rate(d, "control_calm", 8)), pct(rate(d, "control_calm", 16))]
     for d in DETECTORS],
    f"Table 2. Share of episodes with at least one alert (calm market, every detector trained on normal calm trading). "
    f"\"Honest large\" is a genuine large order of the same size, left on the book. A random 40-step stretch of normal "
    f"trading contains an alert about {pct(chance_calm)} of the time (chance level).")

t_auc = table(
    ["Detector", "Spoof vs normal, 16×", "Spoof vs honest, 8×", "Spoof vs honest, 16×", "Layered vs honest, 16×"],
    [[NAMES[d], dec(auc(d, "spoof_calm", "normal", 16).auc), dec(auc(d, "spoof_calm", "genuine", 8).auc),
      f"{dec(auc(d, 'spoof_calm', 'genuine', 16).auc)} ({ci(auc(d, 'spoof_calm', 'genuine', 16), fmt=dec)})",
      dec(auc(d, "layer_calm", "genuine", 16).auc)] for d in DETECTORS],
    "Table 3. Area under the ROC curve (AUC). It needs no threshold: 0.50 means the detector cannot tell the two groups "
    "apart, 1.00 means it separates them perfectly, and below 0.50 means it finds the honest group more unusual.")

t_vol = table(
    ["Detector", "Calm → calm", "Calm → volatile", "Mixed → volatile", "Spoofs 16×, volatile (calm-trained)"],
    [[NAMES[d], pct(metric(d, "normal_calm", "false_alarm_rate").value, 1), pct(metric(d, "normal_volatile", "false_alarm_rate").value, 1),
      pct(metric(d, "normal_volatile", "false_alarm_rate", cond="mixed-trained").value, 1), pct(rate(d, "spoof_volatile", 16))]
     for d in DETECTORS],
    "Table 4. Legitimate volatility. False alarms are the share of bars in normal sessions, with no spoofing at all, "
    "that raise an alert; the target is 1%. \"Mixed\" detectors were trained on calm and volatile trading.")

t_delay = table(
    ["Detector", "Spoofs 8×", "Spoofs 16×", "Layered 16×", "Spoofs 16×, volatile"],
    [[NAMES[d]] + [f"{metric(d, t, 'mean_delay_steps', s).value:.1f}" for t, s in
                   [("spoof_calm", 8), ("spoof_calm", 16), ("layer_calm", 16), ("spoof_volatile", 16)]] for d in ["Rule", "PCA (informed)"]],
    "Table 5. Detection delay: mean number of steps from the wall appearing to the first alert, among episodes that were "
    "caught. Only detectors that catch most spoofs are shown, because the delays of rare, mostly chance alerts are not meaningful.")


def ladder_rows(size):
    lstm = "LSTM-AE (generic)"
    exb = exq("spoofs and honest large orders", size)
    med = lambda c: pct(exb[c].median())
    return [
        ["0. Nothing (LSTM autoencoder)", pct(rate(lstm, "spoof_calm", size)), pct(rate(lstm, "layer_calm", size)),
         pct(rate(lstm, "control_calm", size)), pct(rev(lstm, "withdrawal_calm", size)), pct(rev(lstm, "reversal_calm", size))],
        ["1. Examples (10 spoofs + 10 honest orders)", med("spoof_walls_caught"), med("layered_caught"), med("genuine_flagged"),
         med("withdrawal_flagged"), med("reversal_flagged")],
        ["2. A pattern (the rule)", pct(rate("Rule", "spoof_calm", size)), pct(rate("Rule", "layer_calm", size)),
         pct(rate("Rule", "control_calm", size)), pct(rev("Rule", "withdrawal_calm", size)), pct(rev("Rule", "reversal_calm", size))],
        ["3. A principle (the legal definition)", pct(pr("spoof_calm", "catch_rate", size).value), pct(pr("layer_calm", "catch_rate", size).value),
         pct(pr("control_calm", "flag_rate", size).value), pct(pr("withdrawal_calm", "flag_rate", size).value),
         pct(pr("reversal_calm", "flag_rate", size).value)],
        ["Control: untaught model on account data", pct(princ("spoof_calm", "catch_rate", size, det=UNTAUGHT_ACC).value),
         pct(princ("layer_calm", "catch_rate", size, det=UNTAUGHT_ACC).value), pct(princ("control_calm", "flag_rate", size, det=UNTAUGHT_ACC).value),
         pct(princ("withdrawal_calm", "flag_rate", size, det=UNTAUGHT_ACC).value), pct(princ("reversal_calm", "flag_rate", size, det=UNTAUGHT_ACC).value)],
    ]


LHEAD = ["Teaching", "Spoofs caught", "Layered caught", "Honest large flagged", "Quick withdrawals flagged", "Changes of mind flagged"]
t_ladder16 = table(LHEAD, ladder_rows(16), "Table 6. The ladder of teaching at 16× a typical order (calm market). Rows 0 and 2 use the same "
                   "spoofs as Part 1; row 3 re-simulates them exactly. For the classifier, values are medians over 30 random sets of examples.")
t_ladder8 = table(LHEAD, ladder_rows(8), "Table 7. The same at 8×.")


def stress_rows():
    out = []
    v = lambda df, setting, test, size, met, det=PRINCIPLE: df[(df.setting == setting) & (df.detector == det) & (df.test == test) &
                                                               ((df.size_mult == size) if size else True) & (df.metric == met)].value
    first = lambda s: pct(s.iloc[0]) if len(s) else "n/a"
    for df, setting, label, det in ([(tp, "main", "Main market", PRINCIPLE)] +
                                    [(tmk, s, f"Market: {s}", PRINCIPLE) for s in tmk.setting.unique()] +
                                    [(tac, s, s[0].upper() + s[1:], PRINCIPLE) for s in tac.setting.unique()] +
                                    [(tev, s, "Attack: " + s.replace("two accounts; ", ""), d) for s, d in
                                     tev[["setting", "detector"]].drop_duplicates().itertuples(index=False)]):
        fa = v(df, setting, "normal_calm", None, "false_alarm_windows", det)
        out.append([label, first(v(df, setting, "spoof_calm", 8, "catch_rate", det)), first(v(df, setting, "spoof_calm", 16, "catch_rate", det)),
                    first(v(df, setting, "layer_calm", 16, "catch_rate", det)), first(v(df, setting, "control_calm", 16, "flag_rate", det)),
                    first(v(df, setting, "withdrawal_calm", 16, "flag_rate", det)), pct(fa.iloc[0], 1) if len(fa) else "n/a"])
    return out


def price_rows():
    out = []
    for r in price.itertuples():
        cost = "" if pd.isna(r.cover_cost_ticks) else f"{r.cover_cost_ticks:+.2f}"
        out.append([r.strategy, f"{r.size_mult}×", f"{r.extra_lots_vs_twin:+.2f} ({r.extra_lots_ci_low:+.2f} to {r.extra_lots_ci_high:+.2f})",
                    pct(r.caught_principle40), pct(r.caught_principle160), pct(r.caught_lifetime), pct(r.caught_rule), cost])
    return out


t_price = table(["Dodge", "Size", "Extra lots vs honest twin (95% CI)", "Caught: 40-step windows", "Caught: 160-step windows",
                 "Caught: order life", "Caught: rule", "Buy-back cost, ticks/lot"], price_rows(),
                "Table 10. The price of evasion. Extra lots: how many more lots the spoofer traded the way it wanted than its honest "
                "twin. Each detector's threshold lets about 1% of normal trading alert.")
t_price_honest = table(["Order-life principle on honest trading", "Value"],
                       [[r.test, pct(r.value, 1)] for r in price_honest.itertuples()],
                       "Table 11. The order-life version of the principle on honest trading.")


t_stress = table(["Setting", "Spoofs 8×", "Spoofs 16×", "Layered 16×", "Honest large 16×", "Quick withdrawals 16×", "False-alarm windows"],
                 stress_rows(), "Table 8. The principle detector under every stress test and attack. Each setting fixes its own "
                 "threshold on its own normal trading (1% of 40-step windows).")

t_markets = table(["Claim (written before the test)", "Main", "Fewer book-readers", "More book-readers", "Thinner book", "Impatient traders"], [],
                  "")  # placeholder, replaced below


def claims_table():
    from run_extensions import base_numbers, checks
    c = checks(sens, base_numbers())
    rows = [[html.escape(r[0])] + [("<b>fails</b>" if x == "fails" else x) for x in r[1:]] for r in c.itertuples(index=False)]
    return table(["Claim", "Main", "Fewer book-readers", "More book-readers", "Thinner book", "Impatient traders"], rows,
                 "Table 9. Each claim from the main experiment, checked in four alternative markets.")


# --- The report -------------------------------------------------------------------
N = dict(
    sessions=f"{n_sessions:,}",
    fill8=f"{fill8.fill_gain * 100:+.0f}", fill8ci=f"{fill8.fill_gain_ci_low * 100:+.0f} to {fill8.fill_gain_ci_high * 100:+.0f}",
    fill16=f"{fill16.fill_gain * 100:+.0f}", layfill8=f"{layfill8.fill_gain * 100:+.0f}",
    shift8=f"{fill8.shift_vs_honest:+.2f}",
    rule8=pct(rate("Rule", "spoof_calm", 8)), rule16=pct(rate("Rule", "spoof_calm", 16)), rulelay16=pct(rate("Rule", "layer_calm", 16)),
    rulethr=f"{rule_thr:.0f}",
    pcainf16=pct(rate("PCA (informed)", "spoof_calm", 16)), pcainfgen16=pct(rate("PCA (informed)", "control_calm", 16)),
    pcainflay16=pct(rate("PCA (informed)", "layer_calm", 16)),
    if16=pct(rate("IForest (generic)", "spoof_calm", 16)), lstm16=pct(rate("LSTM-AE (generic)", "spoof_calm", 16)),
    chance=pct(chance_calm),
    lstmauc=dec(lstm_auc16.auc), lstmaucci=ci(lstm_auc16, fmt=dec),
    aucmax=dec(max(untaught_auc16)), aucmin=dec(min(untaught_auc16)),
    volmin=pct(min(vol_fpr)), volmax=pct(max(vol_fpr)), mixmin=pct(min(mix_fpr), 1), mixmax=pct(max(mix_fpr), 1),
    rulevol=pct(metric("Rule", "normal_volatile", "false_alarm_rate").value, 1),
    ordauc=dec(ord16.auc_spoof_vs_genuine), ordnormal=dec(ord16.auc_spoof_vs_normal), ordnosize=dec(ord_nosize.auc_spoof_vs_normal),
    resnormal=dec(row(res, detector="LSTM-AE (generic)").auc_spoof_vs_normal_16),
    resgen=dec(row(res, detector="LSTM-AE (generic)").auc_spoof_vs_genuine_16),
    ruledelay=f"{metric('Rule', 'spoof_calm', 'mean_delay_steps', 16).value:.0f}",
    pr8=pct(pr("spoof_calm", "catch_rate", 8).value), pr16=pct(pr("spoof_calm", "catch_rate", 16).value),
    prl8=pct(pr("layer_calm", "catch_rate", 8).value), prl16=pct(pr("layer_calm", "catch_rate", 16).value),
    prpaid16=pct(pr("spoof_calm", "catch_rate_when_it_paid", 16).value), prpaid8=pct(pr("spoof_calm", "catch_rate_when_it_paid", 8).value),
    prgen=pct(pr("control_calm", "flag_rate", 16).value), prwd=pct(pr("withdrawal_calm", "flag_rate", 16).value),
    prrev=pct(pr("reversal_calm", "flag_rate", 16).value), praucrev=dec(pr("spoof_calm", "auc_vs_reversal", 16).value),
    prfpr=pct(pr("normal_calm", "false_alarm_windows").value, 1), prfprvol=pct(pr("normal_volatile", "false_alarm_windows").value, 1),
    prvol16=pct(pr("spoof_volatile", "catch_rate", 16).value), prthr=f"{pr('normal_calm', 'false_alarm_windows').threshold:.0f}",
    vsrule=f"{pr_vs_rule.difference * 100:+.0f}", vsrulep="p < 0.001" if pr_vs_rule.p_value < 0.001 else f"p = {pr_vs_rule.p_value:.3f}",
    ua16=pct(princ("spoof_calm", "catch_rate", 16, det=UNTAUGHT_ACC).value),
    uaaucgen=dec(princ("spoof_calm", "auc_vs_genuine", 16, det=UNTAUGHT_ACC).value),
    uaaucnorm=dec(princ("spoof_calm", "auc_vs_normal", 16, det=UNTAUGHT_ACC).value),
    uafprvol=pct(princ("normal_volatile", "false_alarm_windows", det=UNTAUGHT_ACC).value, 1),
    exonlygen=pct(ex_only16.genuine_flagged.median()), exonlylay=pct(ex_only16.layered_caught.median()),
    exbothlay16=pct(ex_both16.layered_caught.median()), exbothlay8=pct(ex_both8.layered_caught.median()),
    exbothwd=pct(ex_both16.withdrawal_flagged.median()),
    rulewd=pct(rev("Rule", "withdrawal_calm")), rulerev=pct(rev("Rule")),
    mkmin=pct(mk_spoof16.min()), mkmax=pct(mk_spoof16.max()), mklmin=pct(mk_layer16.min()), mklmax=pct(mk_layer16.max()),
    omni8=pct(princ("spoof_calm", "catch_rate", 8, setting=omni20, df=tac).value),
    omni16=pct(princ("spoof_calm", "catch_rate", 16, setting=omni20, df=tac).value),
    ev1=pct(evs("one account", "spoof_calm", 16, "catch_rate").value), ev2=pct(evs("links", "spoof_calm", 16, "catch_rate").value),
    ev3=pct(evs("every pair", "spoof_calm", 16, "catch_rate").value), ev3wd=pct(evs("every pair", "withdrawal_calm", 16, "flag_rate").value),
    pnone40=pct(row(price, strategy="no evasion", size_mult=16).caught_principle40),
    ppat40=pct(row(price, strategy="patient: 40 steps", size_mult=16).caught_principle40),
    ppat160w=pct(row(price, strategy="patient: 160 steps", size_mult=16).caught_principle160),
    ppat160life=pct(row(price, strategy="patient: 160 steps", size_mult=16).caught_lifetime),
    pnonelife=pct(row(price, strategy="no evasion", size_mult=16).caught_lifetime),
    pcov3=pct(row(price, strategy="buys back all 3 lots", size_mult=16).caught_lifetime),
    pcov3lots=f"{abs(row(price, strategy='buys back all 3 lots', size_mult=16).extra_lots_vs_twin):.1f}",
    pcov3cost=f"{row(price, strategy='buys back all 3 lots', size_mult=16).cover_cost_ticks:.1f}",
    pcov1=pct(row(price, strategy="buys back 1 of 3 lots", size_mult=16).caught_lifetime),
    hfpr=pct(price_honest.value.iloc[0], 1), hfprvol=pct(price_honest.value.iloc[1], 1),
    hgen=pct(price_honest.value.iloc[2]), hwd=pct(price_honest.value.iloc[3]), hrev=pct(price_honest.value.iloc[4]),
)

CSS = """
:root { --ink:#16181d; --ink2:#4b505a; --line:#d7dae0; --mark:#b1245c; --paper:#ffffff; }
* { box-sizing: border-box; }
body { margin: 0; background: #eef0f3; color: var(--ink); font: 16px/1.62 "STIX Two Text", Cambria, Georgia, serif; }
.page { max-width: 46rem; margin: 2.5rem auto; padding: 3rem 3.4rem; background: var(--paper); box-shadow: 0 1px 3px rgb(0 0 0 / .08), 0 16px 40px -20px rgb(0 0 0 / .25); }
h1, h2, h3, .meta, figcaption, table, .abstract h2, .toc { font-family: "Archivo", "Segoe UI", system-ui, sans-serif; }
h1 { font-size: 1.85rem; line-height: 1.15; letter-spacing: -0.02em; margin: 0 0 .6rem; }
.sub { font-family: "Archivo", "Segoe UI", sans-serif; font-size: 1.05rem; color: var(--ink2); margin: 0 0 1.2rem; }
.meta { font-size: .85rem; color: var(--ink2); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: .55rem 0; margin-bottom: 1.6rem; }
h2 { font-size: 1.2rem; margin: 2.2rem 0 .6rem; padding-top: .4rem; border-top: 2px solid var(--ink); }
h3 { font-size: 1rem; margin: 1.5rem 0 .4rem; }
p { margin: 0 0 .85rem; text-align: left; hyphens: auto; }
.abstract { background: #f5f6f8; border-left: 3px solid var(--mark); padding: .9rem 1.1rem; margin: 0 0 1.4rem; }
.abstract h2 { border: 0; margin: 0 0 .35rem; padding: 0; font-size: .95rem; text-transform: uppercase; letter-spacing: .06em; }
.answer { font-family: "Archivo", "Segoe UI", sans-serif; font-weight: 700; }
figure { margin: 1.2rem 0 1.4rem; }
figure.tbl { overflow-x: auto; -webkit-overflow-scrolling: touch; }
figure.tbl table { min-width: 34rem; }
@media print { figure.tbl { overflow: visible; } figure.tbl table { min-width: 0; } }
figure.fig img { width: 100%; height: auto; border: 1px solid var(--line); }
figcaption { font-size: .78rem; line-height: 1.45; color: var(--ink2); margin: .35rem 0 .5rem; }
table { width: 100%; border-collapse: collapse; font-size: .76rem; line-height: 1.35; }
th, td { padding: .32rem .4rem; border-bottom: 1px solid var(--line); vertical-align: top; text-align: left; }
thead th { border-bottom: 1.5px solid var(--ink); font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
ol.refs { font-size: .85rem; padding-left: 1.2rem; }
ol.refs li { margin-bottom: .35rem; }
code { font-family: Consolas, monospace; font-size: .85em; background: #f1f2f4; padding: 0 .2em; }
.note { font-size: .85rem; color: var(--ink2); }
a { color: var(--mark); }
@media (max-width: 700px) { .page { margin: 0; padding: 1.4rem 1rem; box-shadow: none; } table { font-size: .7rem; } }
@media print {
  body { background: #fff; font-size: 10.5pt; }
  .page { max-width: none; margin: 0; padding: 0; box-shadow: none; }
  h2 { break-after: avoid; } figure, table, tr { break-inside: avoid; }
  .noprint { display: none; }
  @page { size: A4; margin: 18mm 17mm 18mm 17mm; }
}
"""

BODY = f"""
<h1>Detecting the Unseen</h1>
<p class=sub>Can artificial intelligence detect hidden market manipulation without being taught what manipulation looks like?</p>
<div class=meta>Ebrahim · Habs Research Scholarship · Technical report on preliminary results · {date.today():%d %B %Y}
<span class=noprint> · <a href="report.pdf">PDF</a> · <a href="index.html">Website</a> · <a href="https://github.com/trader213132/detecting-the-unseen">Code and data</a></span></div>

<section class=abstract><h2>Abstract</h2>
<p>Spoofing means placing large orders one does not intend to trade, so that other traders misread supply and demand. Real
examples are rare and hard to label, which makes one idea attractive: train a detector only on normal trading and let it flag
whatever looks unusual. I tested that idea in an agent-based simulation of a limit order book in which spoofing measurably works
(an 8× fake wall raised the chance of the spoofer's real order filling by {N['fill8']} percentage points). Detectors that learned only
normal trading (PCA, Isolation Forest, sequence PCA and an LSTM autoencoder) could not tell a spoof from an honest large order of the
same size (AUC {N['aucmin']}–{N['aucmax']}), and they raised false alarms on {N['volmin']}–{N['volmax']} of normal bars when the market
became volatile. A hand-written rule caught {N['rule16']} of large spoofs but {N['rulelay16']} once the same spoof was split into smaller
orders. A second experiment gave detectors increasing amounts of prior knowledge. Labelled examples and the rule both learned what
spoofs look like and missed the split version. A detector built only from the legal definition of the offence, which asks whether a
trader showed interest on one side, withdrew it and traded the other way, caught {N['prl16']} of split spoofs with no examples at all,
flagged {N['prgen']} of honest large orders, and kept its false alarms at {N['prfprvol']} in a volatile market. A third experiment
tried to dodge it: every dodge tested either gave up the spoofer's gain or needed two accounts the regulator could not link. No detector could
distinguish a spoof from an honest trader who changes their mind, because only the intention differs.</p>
<p class=answer>Answer: not by looking for the unusual; yes, by knowing the purpose, given who placed each order.</p></section>

<h2>1. Introduction</h2>
<p>Every exchange keeps a limit order book: the list of buy orders (bids) and sell orders (asks) waiting at each price. Traders read
it to judge supply and demand, which is what a spoofer exploits. In <i>Urra, Lopez Gonzalez &amp; Sheth v FCA</i> (Upper Tribunal,
July 2025) three bond traders placed large orders a tick or two behind the best price, a small genuine order on the other side, and
cancelled the large orders within seconds, often just after the small order traded [9].</p>
<p>Supervised machine learning needs many labelled examples of manipulation, which regulators rarely have. Unsupervised anomaly
detection avoids labels: it learns normal behaviour and flags departures from it. Earlier work used generative and recurrent models
trained on normal data [5, 7] and hidden Markov models with anomaly states [1]; Wang and Wellman built agent-based models in which
spoofing is profitable [10, 11]; Fabre and Challet modelled how spoofable a book is [2]. The question here is narrower and, I think,
more basic: is <i>unusual</i> the right target at all?</p>

<h2>2. Research question and hypotheses</h2>
<p><b>Question.</b> Can a detector that is never shown an example of spoofing tell spoofing apart from honest trading?</p>
<p><b>H1 (stated before the experiments).</b> Label-free detectors trained only on normal trading will catch synthetic spoofs more
reliably than a hand-written surveillance rule, especially on variants the rule was not written for.<br>
<b>H2.</b> Detectors that read a sequence of time steps will do better than detectors that read one step at a time.<br>
<b>H3 (added after Part 1).</b> A detector given the definition of the offence, but no examples, will separate spoofs from honest
large orders where unusualness-based detectors could not.<br><b>H4 (added after Part 2).</b> A spoofer who knows about that detector cannot dodge it without giving up what the spoof was for.</p>
<p>Because "catching" is meaningless without false alarms, every detector is also tested on honest large orders, on a volatile but
honest market, and in Part 2 on honest traders who cancel quickly or change their mind.</p>

<h2>3. Method</h2>
<h3>3.1 A market where spoofing can work</h3>
<p>The simulator (written for this project, <code>src/orderbook.py</code>, <code>src/market.py</code>) is a price-time-priority limit order
book with four kinds of normal trader: zero-intelligence traders who trade around a noisy estimate of value; book-reading traders who
lean towards buying when bids outweigh asks (after Wang and Wellman's book-reading agents [10]); two market makers who quote both sides
and cancel and replace every five steps, so quick cancellations are normal; and an institution that occasionally rests a genuinely large
order. A calm and a volatile regime differ in how noisy and jumpy the underlying value is. In total {N['sessions']} sessions of 2,000
steps were simulated for Part 1, each with its own random seed; training, threshold-setting and test sessions never share a seed.</p>
<h3>3.2 Spoofing and honest episodes</h3>
<p><b>Spoof:</b> a large wall one or two ticks behind the best price and a small genuine order (3 lots) at the best price on the other
side; the wall is cancelled when the small order trades or after 30 steps. <b>Layered spoof:</b> the same total size split over four
price levels. <b>Honest twin:</b> the same session and seed with the small order but no wall, to measure what the wall achieves.
<b>Honest large order:</b> a genuine order of the same size and placement left on the book for 150–400 steps. Part 2 adds
<b>quick withdrawal</b> (an honest large order cancelled after 5–25 steps, nothing traded) and <b>change of mind</b> (the same,
followed by a small trade the other way). Wall sizes are 1, 2, 4, 8 and 16 times a typical order.</p>
<h3>3.3 Detectors</h3>
<p>The market is summarised every five steps (a "bar") by 18 generic features (depth at five price levels, spread, price change, and
counts and volumes of orders, cancellations and trades), and optionally six "spoof-informed" features chosen because I knew what spoofing
looks like. Detectors: the <b>rule</b> (the largest order cancelled within 50 steps; its alert threshold, set on normal data, is
{N['rulethr']} lots); <b>PCA</b> (reconstruction error, a linear autoencoder); <b>Isolation Forest</b> [6], written from scratch; and two
sequence models that read eight bars, <b>sequence PCA</b> and an <b>LSTM autoencoder</b> [3, 7]. All are fitted on normal calm sessions only.</p>
<h3>3.4 Scoring</h3>
<p>Each detector's alert threshold is the 99th percentile of its scores on separate normal sessions (about 1% of normal bars alert),
fixed before any spoofing data is seen. An episode is caught if any bar in its eight-bar window alerts. The chance level is how often a
random window of normal trading contains an alert anyway ({N['chance']}). Threshold-free separation is measured with AUC. Intervals
are 95% bootstrap intervals over episodes, and detectors are compared on the same episodes with a paired bootstrap.</p>
<h3>3.5 Part 2: account-level detectors</h3>
<p>Part 2 records which account placed each order, as regulators can: trading venues must keep order records that identify the client
[8]. Account numbers come from a separate random stream, so the market is identical event for event (this is tested). For each account
and each 40-step window the simulator counts lots added, cancelled and traded on each side. The <b>principle detector</b> turns the legal
definition of manipulation (Market Abuse Regulation, Article 12: orders giving false or misleading signals about supply or demand [4])
into three clauses: the account <i>showed</i> interest on one side (submitted more there than on the other), <i>withdrew</i> it rather
than trading it (cancelled more on that side), and <i>traded the other way</i> on balance. Its score is the size of that false signal in
lots; it is never trained, and its threshold is set so that 1% of normal 40-step windows contain an alert ({N['prthr']} lots). Its control
is an untaught Isolation Forest given exactly the same account data. The <b>examples</b> rung is a logistic regression on four order
features (size, lifetime, fraction traded, distance from the best price) shown k labelled spoof walls, and in a second version k
labelled honest large orders too, tested on held-out sessions.</p>

<h2>4. Results</h2>
<h3>4.1 Spoofing works in this market</h3>
<p>An 8× wall raised the chance that the spoofer's genuine order filled by {N['fill8']} points ({N['fill8ci']}) compared with its honest
twin, and a 16× wall by {N['fill16']}; layering worked too ({N['layfill8']} points at 8×). Prices moved about {N['shift8']} ticks in the
spoofer's favour at 8× (Table 1). Missing these spoofs therefore matters.</p>
{t_impact}
{fig('fig4_spoof_impact.png', 'Figure 1. What the wall achieves: extra chance that the genuine order fills, by wall size.')}

<h3>4.2 Label-free detectors barely beat chance; the rule catches only its own pattern</h3>
<p>The untaught detectors caught few spoofs: the Isolation Forest {N['if16']} and the LSTM autoencoder {N['lstm16']} of even the largest,
against a chance level of {N['chance']}. Adding spoof-informed features let PCA catch {N['pcainf16']}, but it also flagged
{N['pcainfgen16']} of honest large orders: it had learned "big order", not "manipulation". The rule caught {N['rule8']} and
{N['rule16']} of single-wall spoofs at 8× and 16×, because its threshold sits between the 4× and 8× sizes; split into four
smaller orders, the same spoof fell under it and the rule caught {N['rulelay16']} (Table 2). <b>H1 is not supported.</b></p>
{t_catch}
{fig('fig2_caught_vs_size.png', 'Figure 2. Share of spoofs caught by wall size, for every detector (calm market).')}

<h3>4.3 They cannot tell a spoof from an honest order of the same size</h3>
<p>Spoofs are somewhat unusual compared with ordinary trading, but against honest large orders of the same size every untaught detector
scored an AUC between {N['aucmin']} and {N['aucmax']}; the LSTM autoencoder scored {N['lstmauc']} ({N['lstmaucci']}), meaning it found
the honest orders <i>more</i> unusual (Table 3). A shuffle test, which scrambles the order of bars inside each window, left the sequence
models' AUCs almost unchanged, so they were not using the order of events. Recomputing features every single step did not help
(LSTM AUC {N['resnormal']} against normal trading, {N['resgen']} against honest orders). <b>H2 is not supported.</b></p>
{t_auc}
{fig('fig6_spoof_vs_genuine_auc.png', 'Figure 3. AUC for separating spoofs from honest orders of the same size, by wall size.')}

<h3>4.4 Legitimate volatility produces false accusations</h3>
<p>When the market became volatile but stayed honest, detectors trained on calm trading flagged {N['volmin']}–{N['volmax']} of normal
bars instead of 1%, while the rule stayed at {N['rulevol']}. Training on calm and volatile trading brought false alarms back to
{N['mixmin']}–{N['mixmax']} (Table 4). An anomaly detector is only as good as its picture of "normal", and an honest market changes.</p>
{t_vol}

<h3>4.5 Detection delay</h3>
<p>Among caught spoofs, the rule's first alert came on average about {N['ruledelay']} steps after the wall appeared (Table 5), when the
wall was cancelled, so after the spoof had already worked. All detectors here, including Part 2's, are after-the-fact surveillance rather
than live prevention; an alert is a reason to look closer, not a trade stopped.</p>
{t_delay}

<h3>4.6 Order by order, and in other markets</h3>
<p>An Isolation Forest trained on every individual order (size, lifetime, fraction traded, distance) found spoof walls unusual against
ordinary orders (AUC {N['ordnormal']}) but ranked every honest large order above every spoof (AUC {N['ordauc']}); without size, spoofs
stopped standing out at all ({N['ordnosize']}). A spoof is unusual only in its size, and its quick cancellation looks like
market-making. Repeating the core experiment in four other markets (Table 9), one claim failed: untaught PCA caught more spoofs in some
markets, but it flagged honest orders just as often, so the central finding, that untaught detectors cannot tell the two apart, held in
every market.</p>
{claims_table()}

<h3>4.7 Part 2: what kind of teaching works</h3>
<p>Shown only labelled spoofs, the classifier learned "large order": it caught every wall, but flagged {N['exonlygen']} of honest large
orders and caught {N['exonlylay']} of layered spoofs. Shown honest large orders as well, it learned "large and short-lived": it stopped
flagging honest orders, but caught {N['exbothlay16']} of layered spoofs at 16× and {N['exbothlay8']} at 8×, and flagged {N['exbothwd']}
of honest quick withdrawals, as did the rule ({N['rulewd']}). More examples (up to 40) changed nothing.</p>
<p>The principle detector caught {N['pr8']} and {N['pr16']} of single-wall spoofs at 8× and 16×, and {N['prl8']} and {N['prl16']} of
layered spoofs, because splitting a wall does not change what the trader showed, withdrew and traded. On the same layered episodes it beat
the rule by {N['vsrule']} points at 16× ({N['vsrulep']}). Almost every spoof it missed never paid off (its small order never traded);
of the spoofs that did, it caught {N['prpaid8']} at 8× and {N['prpaid16']} at 16×. It flagged {N['prgen']} of honest large orders and
{N['prwd']} of honest quick withdrawals, and its false alarms barely moved in a volatile market ({N['prfpr']} to {N['prfprvol']} of
windows). The untaught Isolation Forest on the same account data caught {N['ua16']}: it ranked spoofers as stranger than honest large
traders (AUC {N['uaaucgen']}) but some honest trader was always stranger still (AUC {N['uaaucnorm']} against ordinary trading). The
success comes from the principle, not the data. <b>H3 is supported</b>, with the limits below.</p>
{t_ladder16}
{t_ladder8}
{fig('fig7_ladder_of_teaching.png', 'Figure 4. The ladder of teaching (16×). Pink: spoofs caught. Grey: honest behaviour flagged.')}

<h3>4.8 The case no detector solved, and attempts to break the principle</h3>
<p>An honest trader who changes their mind performs exactly the actions of a spoofer. The principle flagged {N['prrev']} of these
(AUC {N['praucrev']} against spoofs: no separation) and the rule {N['rulerev']}. The principle held in all four alternative markets
({N['mkmin']}–{N['mkmax']} of spoofs and {N['mklmin']}–{N['mklmax']} of layered spoofs at 16×) and however many traders shared an
account. Its weaknesses are accounts: inside a broker account carrying 20% of all orders it caught {N['omni8']} at 8× and {N['omni16']}
at 16×, and a spoofer who shows the wall from one account and trades from another escaped completely ({N['ev1']}) unless the accounts
were linked to their owner ({N['ev2']}). Checking every pair of accounts without links caught {N['ev3']}, but also flagged {N['ev3wd']}
of honest quick withdrawals (Table 8).</p>
{t_stress}

<h3>4.9 Part 3: the price of evasion</h3>
<p>A detector is only useful if a spoofer cannot simply step around it, so the spoofer was given the obvious dodges. <b>Patience</b>,
leaving the wall up after the genuine order traded, beat the 40-step windows of Part 2 at almost no cost (16× catch rate
{N['pnone40']} → {N['ppat40']} with a 40-step wait), and longer windows only help until the spoofer waits longer still
({N['ppat160w']} with 160-step windows against a 160-step wait). Judging every withdrawn order over its own life instead, from the step it
was placed to the step it was withdrawn, closed the gap: {N['ppat160life']} of the most patient spoofers were caught (against
{N['pnonelife']} with no dodge). On honest trading this version kept false alarms at {N['hfpr']} of windows ({N['hfprvol']} when volatile)
and flagged {N['hgen']} of honest large orders, {N['hwd']} of honest quick withdrawals and, as expected, {N['hrev']} of honest changes of
mind. <b>Buying back</b> what was sold made no difference until the spoofer bought back all of it ({N['pcov1']} caught after buying back one
lot); buying back everything escaped ({N['pcov3']} caught) but left the spoofer {N['pcov3lots']} lots worse off than its honest twin,
having paid about {N['pcov3cost']} ticks per lot. Combined with Part 1 (walls below 8× do not help the spoofer) and Part 2 (two accounts escape
unless linked to their owner), every dodge tried either throws away the benefit or depends on accounts the regulator cannot link.
<b>H4 is supported</b> for the dodges tested, which are not every possible strategy.</p>
{t_price}
{t_price_honest}
{fig('fig8_price_of_evasion.png', 'Figure 5. The price of evasion (16× walls): what each dodge keeps against how often it is still caught.')}

<h2>5. Discussion</h2>
<p>The untaught detectors did what they were built to do: they found what was unusual. The trouble is that a working spoof is designed
to be unusual in only one way, its size, and honest large orders are just as big. Unusualness and manipulation are different targets.
Detectors taught by examples or by a rule did better, but they learned the <i>look</i> of the spoofs they were given, so a spoofer who
changes the look, here by splitting the wall, escapes. The legal definition describes the <i>purpose</i> instead: a signal shown, then
withdrawn, to help a trade on the other side. That survives a change of look, but it needs to know who placed each order, and it reaches a
hard limit: behaviour can show that a signal was false, but not why it was sent. That is why the law asks for intent to be proved, and
why an alert should start an investigation rather than end one.</p>

<h2>6. Limitations</h2>
<p>The results describe a simulation I designed, not real markets; real traders, latency and accounts are richer and messier. The rule's
success is partly circular because it was written knowing the pattern, which is why the layering test exists. The principle detector was
designed after Part 1 by someone who knew how the spoofer worked; it encodes the law rather than the spoofer's settings and was tested on
cases it was not tuned for, but it remains one reading of the law. Samples are about 60–80 spoof episodes per size, so intervals are wide.
Agents do not learn or respond strategically to surveillance. No result here is evidence about any real trader.</p>

<h2>7. Conclusion and further work</h2>
<p>A detector cannot find this manipulation by looking for the unusual. It can find it by looking for the purpose, given who placed each
order, and nothing found here separates manipulation from an honest change of mind. Next steps, for Sixth Form: compare the simulator with
real order-book data; let the spoofer learn its own dodges rather than trying ones I chose; study how regulators could link accounts to
their owners; and extend the account-level approach to wash trading using graph methods.</p>

<h2>Reproducibility and use of AI tools</h2>
<p class=note>All code, data-generation seeds and results are public at <a href="https://github.com/trader213132/detecting-the-unseen">github.com/trader213132/detecting-the-unseen</a>.
<code>python run_experiments.py</code>, <code>python run_extensions.py</code> and <code>python run_teaching.py</code> reproduce every number;
<code>python -m pytest</code> runs 25 tests; this report is written by <code>python build_report.py</code> from the results files.
AI assistants (Claude and ChatGPT) were used to help write code and draft text; the experiments, checks and conclusions are my responsibility.
All spoofing happens inside an offline simulation.</p>

<h2>References</h2>
<ol class=refs>
<li>Cao, Y., Li, Y., Coleman, S., Belatreche, A. &amp; McGinnity, T. M. (2015). Adaptive hidden Markov model with anomaly states for price manipulation detection. <i>IEEE Transactions on Neural Networks and Learning Systems</i>, 26(2), 318–330.</li>
<li>Fabre, T. &amp; Challet, D. (2025). Learning the spoofability of limit order books with interpretable probabilistic neural networks. arXiv:2504.15908.</li>
<li>Hochreiter, S. &amp; Schmidhuber, J. (1997). Long short-term memory. <i>Neural Computation</i>, 9(8), 1735–1780.</li>
<li>Regulation (EU) No 596/2014 on market abuse (Market Abuse Regulation), Article 12 and Annex I, as retained in UK law.</li>
<li>Leangarun, T., Tangamchit, P. &amp; Thajchayapong, S. (2018). Stock price manipulation detection using generative adversarial networks. <i>IEEE Symposium Series on Computational Intelligence</i>.</li>
<li>Liu, F. T., Ting, K. M. &amp; Zhou, Z.-H. (2008). Isolation Forest. <i>IEEE International Conference on Data Mining</i>.</li>
<li>Malhotra, P., Ramakrishnan, A., Anand, G., Vig, L., Agarwal, P. &amp; Shroff, G. (2016). LSTM-based encoder-decoder for multi-sensor anomaly detection. arXiv:1607.00148.</li>
<li>Commission Delegated Regulation (EU) 2017/580 (RTS 24) on the maintenance of relevant data relating to orders in financial instruments, as retained in UK law.</li>
<li><i>Urra, Lopez Gonzalez &amp; Sheth v Financial Conduct Authority</i> (2025). Upper Tribunal (Tax and Chancery Chamber), decision of 1 July 2025.</li>
<li>Wang, X. &amp; Wellman, M. P. (2017). Spoofing the limit order book: an agent-based model. <i>Proceedings of AAMAS 2017</i>.</li>
<li>Wang, X., Hoang, C., Vorobeychik, Y. &amp; Wellman, M. P. (2021). Spoofing the limit order book: a strategic agent-based analysis. <i>Games</i>, 12(2), 46.</li>
</ol>
"""


def main():
    page = (f"<!doctype html><html lang=en-GB><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width, initial-scale=1'>"
            f"<title>Detecting the Unseen: research report</title>"
            f"<link rel=preconnect href=https://fonts.googleapis.com><link rel=preconnect href=https://fonts.gstatic.com crossorigin>"
            f"<link rel=stylesheet href='https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=STIX+Two+Text:ital,wght@0,400;0,600;1,400&display=swap'>"
            f"<style>{CSS}</style></head><body><main class=page>{BODY}</main></body></html>")
    out = DOCS / "report.html"
    out.write_text(page, encoding="utf-8")
    print("wrote", out)
    chrome = next((c for c in CHROME if c.exists()), None)
    if chrome:
        pdf = DOCS / "report.pdf"
        subprocess.run([str(chrome), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                        f"--print-to-pdf={pdf}", out.resolve().as_uri()], check=True, capture_output=True, timeout=120)
        print("wrote", pdf)
    else:
        print("Chrome not found: open docs/report.html and print it to PDF")


if __name__ == "__main__":
    main()
