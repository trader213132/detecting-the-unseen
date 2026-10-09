# Part 2: what kind of teaching makes manipulation detectable?

All numbers come from simulated markets. Brackets are 95% bootstrap intervals. Alert thresholds: 1% of normal 40-step windows contain any alert (account detectors), which is stricter than the main experiment's 1% of bars.

## The principle detector vs an untaught detector on the same account data

| Detector | Test | 1× | 2× | 4× | 8× | 16× |
|---|---|---|---|---|---|---|
| Principle (accounts) | Spoofs caught | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 81% (72%–90%) | 92% (86%–98%) |
| Principle (accounts) | Layered spoofs caught | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 85% (77%–93%) | 85% (75%–93%) |
| Principle (accounts) | Spoofs caught, volatile market | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 70% (60%–80%) | 82% (74%–90%) |
| Principle (accounts) | Genuine large orders flagged | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) |
| Principle (accounts) | Honest quick withdrawals flagged | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) |
| Principle (accounts) | Honest changes of mind flagged | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 88% (80%–95%) | 92% (85%–98%) |
| Untaught IForest (accounts) | Spoofs caught | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) |
| Untaught IForest (accounts) | Layered spoofs caught | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) |
| Untaught IForest (accounts) | Spoofs caught, volatile market | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) |
| Untaught IForest (accounts) | Genuine large orders flagged | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) |
| Untaught IForest (accounts) | Honest quick withdrawals flagged | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) |
| Untaught IForest (accounts) | Honest changes of mind flagged | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) | 0% (0%–0%) |

| Detector | False-alarm windows, calm | False-alarm windows, volatile (never trained on it) | Threshold |
|---|---|---|---|
| Principle (accounts) | 0.7% | 0.9% | 10 |
| Untaught IForest (accounts) | 1.9% | 6.6% | 0.775 |

AUC (threshold-free), 16×:

| Detector | Spoof vs genuine | Layered vs genuine | Spoof vs normal | Spoof vs honest change of mind |
|---|---|---|---|---|
| Principle (accounts) | 0.96 (0.93–0.99) | 0.93 (0.88–0.97) | 0.94 (0.89–0.98) | 0.50 (0.46–0.55) |
| Untaught IForest (accounts) | 1.00 (1.00–1.00) | 1.00 (1.00–1.00) | 0.00 (0.00–0.00) | 0.63 (0.53–0.74) |

## Same episodes, compared (paired bootstrap)

| A | B | Test | Size | A | B | A − B (95% CI) | p |
|---|---|---|---|---|---|---|---|
| Principle (accounts) | Rule | spoof_calm | 4× | 0% | 8% | -8 pts (-14 to -2) | 0.004 |
| Principle (accounts) | Rule | spoof_calm | 8× | 81% | 100% | -19 pts (-28 to -11) | 0.000 |
| Principle (accounts) | Rule | spoof_calm | 16× | 92% | 100% | -8 pts (-14 to -2) | 0.003 |
| Principle (accounts) | Rule | layer_calm | 4× | 0% | 10% | -10 pts (-18 to -3) | 0.003 |
| Principle (accounts) | Rule | layer_calm | 8× | 85% | 7% | +78 pts (+68 to +88) | 0.000 |
| Principle (accounts) | Rule | layer_calm | 16× | 85% | 8% | +77 pts (+65 to +87) | 0.000 |
| Principle (accounts) | Rule | control_calm | 4× | 0% | 3% | -3 pts (-10 to +0) | 0.701 |
| Principle (accounts) | Rule | control_calm | 8× | 0% | 7% | -7 pts (-17 to +0) | 0.254 |
| Principle (accounts) | Rule | control_calm | 16× | 0% | 0% | +0 pts (+0 to +0) | 1.000 |
| Principle (accounts) | PCA (informed) | spoof_calm | 4× | 0% | 9% | -9 pts (-15 to -2) | 0.001 |
| Principle (accounts) | PCA (informed) | spoof_calm | 8× | 81% | 38% | +44 pts (+31 to +56) | 0.000 |
| Principle (accounts) | PCA (informed) | spoof_calm | 16× | 92% | 98% | -5 pts (-12 to +1) | 0.197 |
| Principle (accounts) | PCA (informed) | layer_calm | 4× | 0% | 10% | -10 pts (-18 to -3) | 0.005 |
| Principle (accounts) | PCA (informed) | layer_calm | 8× | 85% | 12% | +73 pts (+60 to +85) | 0.000 |
| Principle (accounts) | PCA (informed) | layer_calm | 16× | 85% | 8% | +77 pts (+65 to +87) | 0.000 |
| Principle (accounts) | PCA (informed) | control_calm | 4× | 0% | 10% | -10 pts (-23 to +0) | 0.075 |
| Principle (accounts) | PCA (informed) | control_calm | 8× | 0% | 23% | -23 pts (-40 to -10) | 0.002 |
| Principle (accounts) | PCA (informed) | control_calm | 16× | 0% | 90% | -90 pts (-100 to -80) | 0.000 |
| Principle (accounts) | IForest (generic) | spoof_calm | 4× | 0% | 8% | -8 pts (-14 to -2) | 0.004 |
| Principle (accounts) | IForest (generic) | spoof_calm | 8× | 81% | 10% | +71 pts (+60 to +81) | 0.000 |
| Principle (accounts) | IForest (generic) | spoof_calm | 16× | 92% | 12% | +80 pts (+70 to +89) | 0.000 |
| Principle (accounts) | IForest (generic) | layer_calm | 4× | 0% | 0% | +0 pts (+0 to +0) | 1.000 |
| Principle (accounts) | IForest (generic) | layer_calm | 8× | 85% | 7% | +78 pts (+68 to +88) | 0.000 |
| Principle (accounts) | IForest (generic) | layer_calm | 16× | 85% | 23% | +62 pts (+47 to +75) | 0.000 |
| Principle (accounts) | IForest (generic) | control_calm | 4× | 0% | 7% | -7 pts (-17 to +0) | 0.251 |
| Principle (accounts) | IForest (generic) | control_calm | 8× | 0% | 7% | -7 pts (-17 to +0) | 0.254 |
| Principle (accounts) | IForest (generic) | control_calm | 16× | 0% | 23% | -23 pts (-40 to -10) | 0.001 |
| Principle (accounts) | LSTM-AE (generic) | spoof_calm | 4× | 0% | 1% | -1 pts (-4 to +0) | 0.729 |
| Principle (accounts) | LSTM-AE (generic) | spoof_calm | 8× | 81% | 6% | +75 pts (+65 to +84) | 0.000 |
| Principle (accounts) | LSTM-AE (generic) | spoof_calm | 16× | 92% | 9% | +84 pts (+74 to +92) | 0.000 |
| Principle (accounts) | LSTM-AE (generic) | layer_calm | 4× | 0% | 2% | -2 pts (-5 to +0) | 0.708 |
| Principle (accounts) | LSTM-AE (generic) | layer_calm | 8× | 85% | 5% | +80 pts (+70 to +90) | 0.000 |
| Principle (accounts) | LSTM-AE (generic) | layer_calm | 16× | 85% | 17% | +68 pts (+55 to +80) | 0.000 |
| Principle (accounts) | LSTM-AE (generic) | control_calm | 4× | 0% | 3% | -3 pts (-10 to +0) | 0.729 |
| Principle (accounts) | LSTM-AE (generic) | control_calm | 8× | 0% | 10% | -10 pts (-23 to +0) | 0.077 |
| Principle (accounts) | LSTM-AE (generic) | control_calm | 16× | 0% | 50% | -50 pts (-67 to -33) | 0.000 |

## The hardest honest case, for every rung of the main experiment

Share of honest episodes flagged (same thresholds as the main experiment). Withdrawal: a large order cancelled after 5-25 steps, nothing traded. Reversal: the same, then a small trade the other way.

| Detector | Case | 1× | 2× | 4× | 8× | 16× |
|---|---|---|---|---|---|---|
| Rule | reversal | 3% | 8% | 2% | 93% | 98% |
| Rule | withdrawal | 5% | 10% | 5% | 93% | 100% |
| PCA (generic) | reversal | 5% | 7% | 8% | 10% | 43% |
| PCA (generic) | withdrawal | 7% | 8% | 8% | 5% | 35% |
| PCA (informed) | reversal | 10% | 10% | 5% | 48% | 98% |
| PCA (informed) | withdrawal | 15% | 7% | 17% | 35% | 95% |
| IForest (generic) | reversal | 3% | 13% | 12% | 10% | 13% |
| IForest (generic) | withdrawal | 8% | 10% | 12% | 5% | 8% |
| IForest (informed) | reversal | 3% | 13% | 5% | 17% | 27% |
| IForest (informed) | withdrawal | 18% | 12% | 10% | 13% | 33% |
| Seq-PCA (generic) | reversal | 2% | 2% | 2% | 7% | 28% |
| Seq-PCA (generic) | withdrawal | 3% | 2% | 3% | 0% | 30% |
| LSTM-AE (generic) | reversal | 3% | 5% | 2% | 8% | 10% |
| LSTM-AE (generic) | withdrawal | 2% | 7% | 3% | 8% | 18% |

## Rung 1: taught by examples

Logistic regression on the four order features, shown k labelled spoof walls (single-wall, 8× and 16×) and 20,000 normal orders; in the second variant also k labelled honest large orders. 30 random draws of examples per k: median (10th–90th percentile). Threshold: 1 normal order in 1,000. Test sessions are never the ones examples came from.

| Shown | k examples | Size | Spoof walls caught | Layered caught | Genuine flagged | Quick withdrawals flagged | Changes of mind flagged | AUC spoof vs genuine |
|---|---|---|---|---|---|---|---|---|
| spoofs only | 1 | 8× | 100% (100%–100%) | 0% (0%–0%) | 92% (41%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 1 | 16× | 100% (100%–100%) | 0% (0%–15%) | 100% (100%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 2 | 8× | 100% (100%–100%) | 0% (0%–0%) | 92% (41%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 2 | 16× | 100% (100%–100%) | 0% (0%–16%) | 100% (100%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 5 | 8× | 100% (100%–100%) | 0% (0%–0%) | 92% (49%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 5 | 16× | 100% (100%–100%) | 0% (0%–15%) | 100% (100%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 10 | 8× | 100% (100%–100%) | 0% (0%–0%) | 92% (82%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 10 | 16× | 100% (100%–100%) | 0% (0%–0%) | 100% (100%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 20 | 8× | 100% (100%–100%) | 0% (0%–0%) | 92% (92%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 20 | 16× | 100% (100%–100%) | 0% (0%–0%) | 100% (100%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 40 | 8× | 100% (100%–100%) | 0% (0%–0%) | 92% (92%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs only | 40 | 16× | 100% (100%–100%) | 0% (0%–0%) | 100% (100%–100%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs and honest large orders | 1 | 8× | 79% (73%–100%) | 0% (0%–0%) | 0% (0%–0%) | 40% (8%–96%) | 19% (12%–100%) | 1.00 |
| spoofs and honest large orders | 1 | 16× | 100% (96%–100%) | 30% (20%–38%) | 0% (0%–34%) | 100% (98%–100%) | 100% (98%–100%) | 1.00 |
| spoofs and honest large orders | 2 | 8× | 73% (69%–100%) | 0% (0%–0%) | 0% (0%–0%) | 29% (8%–96%) | 15% (8%–100%) | 1.00 |
| spoofs and honest large orders | 2 | 16× | 100% (92%–100%) | 30% (15%–38%) | 0% (0%–42%) | 100% (86%–100%) | 100% (75%–100%) | 1.00 |
| spoofs and honest large orders | 5 | 8× | 73% (73%–89%) | 0% (0%–0%) | 0% (0%–0%) | 29% (8%–62%) | 12% (8%–38%) | 1.00 |
| spoofs and honest large orders | 5 | 16× | 100% (96%–100%) | 30% (30%–30%) | 0% (0%–0%) | 100% (96%–100%) | 100% (100%–100%) | 1.00 |
| spoofs and honest large orders | 10 | 8× | 73% (73%–88%) | 0% (0%–0%) | 0% (0%–0%) | 29% (25%–62%) | 17% (12%–29%) | 1.00 |
| spoofs and honest large orders | 10 | 16× | 100% (96%–100%) | 30% (30%–30%) | 0% (0%–0%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs and honest large orders | 20 | 8× | 73% (73%–77%) | 0% (0%–0%) | 0% (0%–0%) | 29% (25%–38%) | 17% (8%–17%) | 1.00 |
| spoofs and honest large orders | 20 | 16× | 100% (100%–100%) | 30% (30%–30%) | 0% (0%–0%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |
| spoofs and honest large orders | 40 | 8× | 73% (73%–73%) | 0% (0%–0%) | 0% (0%–0%) | 29% (29%–29%) | 17% (17%–17%) | 1.00 |
| spoofs and honest large orders | 40 | 16× | 100% (100%–100%) | 30% (30%–30%) | 0% (0%–0%) | 100% (100%–100%) | 100% (100%–100%) | 1.00 |

## Stress test: four alternative markets

| Setting | Detector | Spoofs 8× | Spoofs 16× | Layered 8× | Layered 16× | Genuine flagged 16× | Quick withdrawals flagged 16× | Changes of mind flagged 16× | False-alarm windows |
|---|---|---|---|---|---|---|---|---|---|
| fewer book-readers | Principle (accounts) | 78% | 80% | 72% | 90% | 0% | 0% | 92% | 0.4% |
| fewer book-readers | Untaught IForest (accounts) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0.9% |
| more book-readers | Principle (accounts) | 86% | 96% | 90% | 90% | 0% | 0% | 88% | 2.1% |
| more book-readers | Untaught IForest (accounts) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0.8% |
| thinner book | Principle (accounts) | 76% | 90% | 78% | 85% | 0% | 0% | 96% | 1.3% |
| thinner book | Untaught IForest (accounts) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0.8% |
| impatient traders | Principle (accounts) | 80% | 88% | 98% | 88% | 0% | 0% | 71% | 0.2% |
| impatient traders | Untaught IForest (accounts) | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 1.0% |

## Stress test: how accounts are organised

| Setting | Detector | Spoofs 8× | Spoofs 16× | Layered 8× | Layered 16× | Genuine flagged 16× | Quick withdrawals flagged 16× | Changes of mind flagged 16× | False-alarm windows |
|---|---|---|---|---|---|---|---|---|---|
| 10 accounts per trader type | Principle (accounts) | 84% | 92% | 80% | 85% | 0% | 0% | 71% | 0.8% |
| 25 accounts per trader type | Principle (accounts) | 84% | 92% | 80% | 85% | 0% | 0% | 71% | 1.8% |
| 50 accounts per trader type | Principle (accounts) | 84% | 92% | 80% | 85% | 0% | 0% | 71% | 1.1% |
| 200 accounts per trader type | Principle (accounts) | 84% | 92% | 80% | 85% | 0% | 0% | 71% | 0.6% |
| 800 accounts per trader type | Principle (accounts) | 84% | 92% | 80% | 85% | 0% | 0% | 71% | 0.3% |
| spoofer inside an omnibus account carrying 1% of all orders | Principle (accounts) | 82% | 94% | 75% | 80% | 0% | 0% | 71% | 0.6% |
| spoofer inside an omnibus account carrying 5% of all orders | Principle (accounts) | 74% | 92% | 70% | 80% | 0% | 0% | 71% | 1.4% |
| spoofer inside an omnibus account carrying 20% of all orders | Principle (accounts) | 42% | 66% | 35% | 72% | 0% | 0% | 71% | 1.0% |
| 20-step windows | Principle (accounts) | 76% | 82% | 70% | 70% | 0% | 0% | 29% | 0.5% |
| 80-step windows | Principle (accounts) | 84% | 92% | 80% | 85% | 0% | 0% | 71% | 1.2% |
| 160-step windows | Principle (accounts) | 86% | 92% | 80% | 85% | 0% | 0% | 71% | 1.8% |

## Attack: a spoofer who uses two accounts

| Setting | Detector | Spoofs 8× | Spoofs 16× | Layered 8× | Layered 16× | Genuine flagged 16× | Quick withdrawals flagged 16× | Changes of mind flagged 16× | False-alarm windows |
|---|---|---|---|---|---|---|---|---|---|
| two accounts; checked one account at a time | Principle (accounts) | 0% | 0% | 0% | 0% | 0% | 0% | 79% | 1.0% |
| two accounts; regulator links accounts to their owner | Principle (accounts) | 88% | 80% | 92% | 88% | 0% | 0% | 79% | 1.0% |
| two accounts; every pair of accounts checked, no links | Principle (any two accounts) | 98% | 100% | 98% | 100% | 4% | 100% | 100% | 0.4% |
