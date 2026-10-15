"""Publish only a complete, hash-verified learning pilot into the existing site."""
import html
import json
import re
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

import build_pages
from run_emergence import hashes

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results/emergence"
DOCS = ROOT / "docs"


def label(policy):
    known = {"honest": "Honest benchmark", "random": "Uniform random", "designed_control": "Designed diagnostic"}
    if policy in known:
        return known[policy]
    fine, number = policy.split("_learner")
    parts = number.split("_", 1)
    suffix = {"sampled": " (sampled)", "no_extra": " (extra removed)"}.get(parts[1] if len(parts)>1 else "", "")
    return f"{'No fine' if fine == 'fine0' else 'Fine 2'}, learner {int(parts[0])+1}{suffix}"


def fnum(value):
    return f"{value:+.3f}"


def table(rows, title, full=False):
    result = f'<div class="emergence-table-wrap" tabindex="0" role="region" aria-label="{title}"><table class="emergence-table"><caption>{title}</caption><thead><tr><th scope="col">Policy</th><th scope="col">Score</th><th scope="col">Gain vs benchmark<br>95% interval</th><th scope="col">Effect of extra order<br>95% interval</th><th scope="col">Signature</th><th scope="col">Rule alerts</th><th scope="col">Visibility alerts</th></tr></thead><tbody>'
    for r in rows:
        if not full and r["policy"].endswith(("_sampled", "_no_extra")):
            continue
        extra = "—" if "extra_effect" not in r else f'{fnum(r["extra_effect"])}<br>({fnum(r["extra_ci_low"])} to {fnum(r["extra_ci_high"])})'
        result += f'<tr><th scope="row">{label(r["policy"])}</th><td>{fnum(r["reward"])}</td><td>{fnum(r["vs_honest"])}<br>({fnum(r["ci_low"])} to {fnum(r["ci_high"])})</td><td>{extra}</td><td>{r["signature_share"]:.0%}</td><td>{r["flag_rule"]:.1%}</td><td>{r["flag_seen"]:.1%}</td></tr>'
    return result + '</tbody></table></div>'


def clean(records):
    return [{k: v for k, v in r.items() if not (isinstance(v, float) and np.isnan(v))} for r in records]


def run():
    manifest = json.loads((OUT / "manifest.json").read_text())
    if manifest["status"] != "complete" or hashes() != manifest["source_sha256"]:
        raise ValueError("Refusing to publish incomplete results or a changed experiment dependency.")
    rows = clean(pd.read_csv(OUT / "summary.csv").to_dict("records"))
    training = pd.read_csv(OUT / "training.csv").to_dict("records")
    calm = [r for r in rows if r["environment"] == "calm"]
    greedy = [r for r in calm if r["policy"].startswith("fine") and not r["policy"].endswith(("_sampled", "_no_extra"))]
    count = sum(r["signature_share"] > .5 for r in greedy)
    positive = sum(r.get("extra_ci_low", -1) > 0 for r in greedy)
    plain = (f'In plain words: all {len(greedy)} AI traders learned ordinary, honest ways to fill the order, and none learned to spoof. '
             if not count else f'In plain words: {count} of {len(greedy)} AI traders ended up choosing a spoof-like order. ')
    conclusion = plain + f'{count} of {len(greedy)} final greedy policies matched the predeclared spoof-like signature. {positive} had a positive extra-order effect with a pointwise 95% interval entirely above zero in the calm test market.'
    if not count:
        verdict = "This pilot did not establish learned spoofing."
    else:
        verdict = "Suspicious choices emerged; manipulation still needs evidence."
    payload = dict(manifest=manifest, summary=rows, training=training)
    (DOCS / "data/emergence.js").write_text("window.EMERGENCE = " + json.dumps(payload, allow_nan=False) + ";\n", encoding="utf-8")
    downloads = DOCS / "data/emergence"
    downloads.mkdir(parents=True, exist_ok=True)
    for name in ["manifest.json", "policies.json", "summary.csv", "training.csv", "episodes.csv", "baseline_validation.csv"]:
        shutil.copy2(OUT / name, downloads / name)
    for name in ["emergence-protocol.md", "emergence-design-prompts.md"]:
        shutil.copy2(ROOT / "research" / name, downloads / name)
    with zipfile.ZipFile(downloads / "reproduce.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for relative in manifest["source_sha256"]:
            z.write(ROOT / relative, relative)
        for p in (ROOT / "src").glob("*.py"):
            if str(p.relative_to(ROOT)).replace('\\', '/') not in manifest["source_sha256"]:
                z.write(p, str(p.relative_to(ROOT)))
        for name in ["requirements.txt", "tests/test_emergence.py", "research/emergence-protocol.md"]:
            z.write(ROOT / name, name)
        for p in OUT.iterdir():
            if p.is_file():
                z.write(p, "evidence/" + p.name)
        z.writestr("REPRODUCE.md", "# Reproduce the pilot\n\nInstall requirements.txt, then run `python run_emergence.py --workers 4`. The saved reference output is in evidence/; a fresh run writes results/emergence/. Seeds and hashes are in evidence/manifest.json. Use the recorded Python and library versions for closest reproduction. Existing output is never overwritten. No broker or exchange connection is used.\n")
    n = manifest["config"]["test"]
    markets = {"calm": "Calm market", "no_feedback": "Book response disabled", "volatile": "Volatile market"}
    tables = "".join(f'<div data-market-table="{env}">{table([r for r in rows if r["environment"] == env], name)}<details><summary>All policies, including sampled choices and no-extra-order twins</summary>{table([r for r in rows if r["environment"] == env], name + ": full comparison", True)}</details></div>' for env, name in markets.items())
    choices = "".join(f'<option value="{i}">Learner {i+1}</option>' for i in range(manifest["config"]["learners"]))
    policies = "".join(f'<li><b>{"No fine" if p["fine"] == 0 else "Fine 2"}, learner {p["learner"]+1}:</b> {html.escape(p["description"])}.</li>' for p in manifest["policies"])
    # Reuse the incumbent head and shared shell, including its fonts and theme.
    old = (DOCS / "experiment.html").read_text(encoding="utf-8")
    head = old.split('</head>')[0]
    head = head.replace('The experiment · Detecting the Unseen', 'Will AI traders learn manipulation? · Detecting the Unseen')
    head = head.replace('Can AI spot market manipulation it was never shown?', 'Will AI traders learn manipulation, and can existing detectors recognise it?')
    head = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*(">)', r'\1A reproducible learning-agent pilot with frozen detectors, paired controls and inspectable evidence. Simulation only; unrestricted emergence is not established.\2', head)
    body = f'''{head}<link rel="stylesheet" href="assets/emergence.css"></head>
<body class="subpage"><div class="lake-scene" aria-hidden="true"><canvas data-lake></canvas></div>
<a class="skip-link" href="#article">Skip to the research</a>
<!-- header:start -->{build_pages.header("learning.html")}<!-- header:end -->
<main id="article"><div class="pagehead"><h1 class="pagehead__title">Will AI traders learn manipulation?</h1>
<p class="pagehead__dek">A learning agent, existing detectors, and a test that can return an honest “not demonstrated”.</p></div>
<div class="emergence-wrap">
<section aria-labelledby="learning-answer"><h2 id="learning-answer">{verdict}</h2><p class="lead">{conclusion}</p>
<p>{len(manifest["policies"])} independently initialised learners completed {manifest["training_episodes"]:,} training episodes. The held-out study contains {manifest["evaluated_episodes"]:,} policy-by-market episodes, using the same {n} test seeds for paired comparisons. Reusing a seed does not create another independent market sample.</p>
<p><b>What this establishes:</b> a reproducible result for a restricted execution learner in this simulator. It does not establish what all AI traders will do, or that an agent invented a strategy outside the choices supplied by its designer.</p>
<div class="emergence-links"><a href="#learning-replay">Inspect the learning</a><a href="#learning-results">Read held-out results</a><a href="data/emergence/reproduce.zip" download>Download reproducible study</a></div></section>
<section aria-labelledby="novelty"><h2 id="novelty">The question has a history.</h2>
<p>Byrd’s <a href="https://arxiv.org/abs/2306.06087">Learning Not to Spoof</a> already reports a profit-seeking agent independently learning spoofing. <a href="https://arxiv.org/abs/1511.00740">Learning Unfair Trading</a> also studies manipulation through reinforcement learning. This chapter is a restricted replication and detector-transfer pilot. Its possible contribution is in the controls and detector comparisons; priority or groundbreaking novelty has not been established.</p>
<p>The earlier <a href="experiment.html">detector experiments</a> remain the foundation. This chapter reverses the direction: let an agent optimise execution, then inspect what it learned and how the old detectors respond.</p></section>
<section id="learning-replay" aria-labelledby="replay-heading"><h2 id="replay-heading">Watch its choices change.</h2>
<p>The bars show saved choice probabilities after each training round. They are measured training output, not a live simulation. Extra size, distance and cancellation probabilities matter only when an extra order is selected.</p>
<div class="emergence-controls" data-learning-controls hidden>
<label>Reward condition<select id="learning-condition"><option value="0">Execution reward only</option><option value="2">Execution reward minus alert penalty</option></select></label>
<label>Independent run<select id="learning-learner">{choices}</select></label>
<button id="learning-play" type="button" aria-pressed="false">Play learning</button>
<label><span id="learning-round-label">Training round</span><input id="learning-round" type="range" min="0" max="99" value="99" aria-label="Training round"></label></div>
<div class="learning-stage" data-learning-stage><p>The final choices below remain available without JavaScript. Download the training table to inspect every probability.</p></div>
<p class="learning-status" id="learning-status" role="status" aria-live="off"></p>
<details open><summary>Every final greedy policy</summary><ul>{policies}</ul></details>
<p class="emergence-note">Playback starts paused, stops offscreen, and respects reduced motion. Pink identifies the opposite-side option; it is not a verdict of manipulation.</p></section>
<section id="learning-results" aria-labelledby="results-heading"><h2 id="results-heading">What survived the controls?</h2>
<p>Score is execution surplus in ticks per client lot relative to the arrival midpoint. Higher is better. The honest benchmark was selected on separate validation sessions. The extra-order effect compares each learned greedy policy with the same policy after its extra order is removed.</p>
<div class="emergence-controls" data-market-controls hidden><label>Test market<select id="learning-market">{''.join(f'<option value="{k}">{v}</option>' for k,v in markets.items())}</select></label></div>
<p id="market-status" role="status">Each row uses {n} independent market sessions. All intervals are pointwise paired 95% bootstrap intervals.</p>{tables}
<p class="emergence-note">“Signature” means the predeclared large opposite-side, early-cancellation configuration. It does not prove intent, actual cancellation without execution, or price impact. Rule alerts are market-wide; visibility alerts are attributed to the agent. These are alert rates, not validated detection sensitivity. The designed diagnostic is a human-written control, never a discovery.</p>
<p class="emergence-note">The intervals do not include uncertainty across training seeds and are not corrected for multiple comparisons. No-feedback removes the imbalance response of both market makers and reactive traders. It tests this simulator’s mechanism; it does not reproduce a real market.</p></section>
<section aria-labelledby="method"><h2 id="method">An experiment designed to be wrong.</h2>
<p>The agent has an ordinary task: buy or sell three lots within 30 simulation steps at the best achievable price. It receives no spoof label or manipulation bonus. A second group pays two ticks per client lot when the frozen visibility detector alerts. Training uses a policy-gradient algorithm called REINFORCE.</p>
<p>All auxiliary fills count. The final inventory must equal the client target, and any terminal adjustment is included in the reward. Fees are absent during training; the downloadable summary includes accounting-only fee sensitivity at 0.01 and 0.1 tick per traded lot.</p>
<p><b>The important restriction:</b> the agent selects its order settings once, rather than reacting at every step. It has no state input. The 843 distinct configurations and the fill-triggered cancellation option were supplied by humans. This is a policy-gradient bandit over execution choices, not an unrestricted trader learning every action from scratch.</p>
<p>Four detectors and their combined alert are inherited from the previous work. Their thresholds are frozen using separate normal-trading data. The table displays the rule and visibility detector; all detector scores, stochastic-policy results, order fills and transaction volumes are available in the downloads.</p>
<p>A convincing manipulation discovery would need a repeatable economic benefit from the misleading order, a matching event trace, and independent confirmation after exploratory analysis. A detector alert or a suspicious configuration is insufficient.</p></section>
<section aria-labelledby="next"><h2 id="next">The next experiment has to be harder.</h2>
<p>Replace the configuration chooser with a state-conditioned agent that submits, cancels or waits at every step. Remove the ready-made fill-triggered cancellation behaviour. Add fees, latency, capital limits and counterparties that do not naively trust displayed depth. Freeze the detectors before training and confirm any promising result on a new, untouched seed set.</p>
<p>The current result sets a baseline for that work. It must not be promoted as proof that AI traders are safe, proof of illegal intent, or a new discovery of autonomous spoofing.</p></section>
<section aria-labelledby="evidence"><h2 id="evidence">Inspect the evidence.</h2>
<div class="emergence-links"><a href="data/emergence/episodes.csv" download>Every test episode</a><a href="data/emergence/summary.csv" download>Results and fee sensitivity</a><a href="data/emergence/training.csv" download>Every training round</a><a href="data/emergence/policies.json" download>Final policy probabilities</a><a href="data/emergence/manifest.json" download>Seeds, settings and source hashes</a><a href="data/emergence/baseline_validation.csv" download>Baseline selection data</a><a href="data/emergence/emergence-protocol.md">Full protocol</a><a href="data/emergence/emergence-design-prompts.md">Design and motion prompts</a></div>
<p class="emergence-note">This pilot has separate files from the earlier unfinished agent experiment. The reproducible bundle includes the exact simulator, learner, calibration inputs and recorded outputs. All trading here is simulated.</p></section>
</div></main><!-- footer:start -->{build_pages.footer("learning.html")}<!-- footer:end -->
<script src="data/results.js"></script><script src="assets/site.js?v=9"></script><script src="assets/masthead.js?v=10"></script>
<script src="data/emergence.js"></script><script src="assets/emergence.js"></script><script type="module" src="assets/lake.js?v=12"></script></body></html>'''
    (DOCS / "learning.html").write_text(body, encoding="utf-8")
    note = f"# Learning-agent pilot\n\n{verdict}\n\n{conclusion}\n\nTraining episodes: {manifest['training_episodes']:,}. Evaluation episodes: {manifest['evaluated_episodes']:,}. Independent paired test seeds: {n}.\n\nThis is a restricted execution-policy bandit, not an unrestricted sequential agent. Related work already reports learned spoofing. See the protocol for the research scope and limitations.\n\n"
    note += "| Policy | Calm score | Difference vs benchmark | 95% interval | Visibility alerts |\n|---|---:|---:|---|---:|\n"
    for r in calm:
        note += f"| {label(r['policy'])} | {fnum(r['reward'])} | {fnum(r['vs_honest'])} | {fnum(r['ci_low'])} to {fnum(r['ci_high'])} | {r['flag_seen']:.1%} |\n"
    (OUT / "findings.md").write_text(note, encoding="utf-8")
    print(verdict, conclusion)
    print("Built docs/learning.html and complete evidence downloads.")


if __name__ == "__main__":
    run()
