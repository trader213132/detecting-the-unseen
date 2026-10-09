# Extension experiments

## Sensitivity: do the conclusions survive a different market?

The core experiment was repeated in four alternative simulated markets (20 training sessions, about 50 episodes per size each). Settings changed: **fewer book-readers** (reactive_share=0.25, mm_react_shift=1.5); **more book-readers** (reactive_share=0.75, mm_react_shift=4.5); **thinner book** (arrival_rate=1.0, mm_size=2); **impatient traders** (mean_patience=20.0).

| claim | main experiment | fewer book-readers | more book-readers | thinner book | impatient traders |
|---|---|---|---|---|---|
| Untaught detectors catch at most 30% of 16× single-wall spoofs | holds | fails | fails | fails | fails |
| (added after seeing the results) Untaught detectors flag honest 16× orders at least as often as they catch 16× spoofs | holds | holds | holds | holds | holds |
| The rule catches at least 90% of 8× and 16× single-wall spoofs | holds | holds | holds | holds | holds |
| Layering drops the rule to at most 30% at 16× | holds | holds | holds | holds | holds |
| No untaught detector tells spoofs from genuine orders (AUC at most 0.6) | holds | holds | holds | holds | holds |
| PCA with spoof-informed features flags at least 50% of genuine 16× orders | holds | holds | holds | holds | holds |
| The 16× wall measurably helps the genuine order fill (CI above zero) | holds | fails | holds | holds | holds |

Key numbers per market:

| Market | Detector | Spoofs 8× | Spoofs 16× | Layered 16× | Genuine flagged 16× | AUC spoof vs genuine 16× | Fill gain 16× |
|---|---|---|---|---|---|---|---|
| fewer book-readers | Rule | 100% | 100% | 5% | 0% | 1.00 | +4% |
| fewer book-readers | PCA (generic) | 2% | 50% | 10% | 50% | 0.51 | +4% |
| fewer book-readers | PCA (informed) | 26% | 98% | 8% | 67% | 0.66 | +4% |
| fewer book-readers | IForest (generic) | 6% | 8% | 10% | 17% | 0.44 | +4% |
| fewer book-readers | IForest (informed) | 8% | 26% | 22% | 12% | 0.49 | +4% |
| fewer book-readers | Seq-PCA (generic) | 6% | 24% | 5% | 42% | 0.42 | +4% |
| fewer book-readers | LSTM-AE (generic) | 0% | 0% | 0% | 0% | 0.28 | +4% |
| more book-readers | Rule | 100% | 100% | 2% | 4% | 1.00 | +20% |
| more book-readers | PCA (generic) | 8% | 34% | 10% | 38% | 0.44 | +20% |
| more book-readers | PCA (informed) | 12% | 60% | 10% | 58% | 0.43 | +20% |
| more book-readers | IForest (generic) | 2% | 22% | 15% | 33% | 0.42 | +20% |
| more book-readers | IForest (informed) | 14% | 30% | 22% | 33% | 0.56 | +20% |
| more book-readers | Seq-PCA (generic) | 6% | 8% | 12% | 25% | 0.39 | +20% |
| more book-readers | LSTM-AE (generic) | 4% | 8% | 10% | 25% | 0.31 | +20% |
| thinner book | Rule | 100% | 100% | 5% | 8% | 1.00 | +22% |
| thinner book | PCA (generic) | 12% | 42% | 10% | 50% | 0.50 | +22% |
| thinner book | PCA (informed) | 10% | 84% | 2% | 75% | 0.59 | +22% |
| thinner book | IForest (generic) | 10% | 16% | 22% | 29% | 0.34 | +22% |
| thinner book | IForest (informed) | 28% | 30% | 18% | 38% | 0.47 | +22% |
| thinner book | Seq-PCA (generic) | 8% | 30% | 15% | 33% | 0.47 | +22% |
| thinner book | LSTM-AE (generic) | 4% | 10% | 8% | 42% | 0.29 | +22% |
| impatient traders | Rule | 100% | 100% | 8% | 0% | 1.00 | +10% |
| impatient traders | PCA (generic) | 10% | 44% | 2% | 54% | 0.43 | +10% |
| impatient traders | PCA (informed) | 26% | 86% | 15% | 88% | 0.47 | +10% |
| impatient traders | IForest (generic) | 10% | 12% | 18% | 17% | 0.34 | +10% |
| impatient traders | IForest (informed) | 36% | 50% | 35% | 58% | 0.42 | +10% |
| impatient traders | Seq-PCA (generic) | 6% | 28% | 12% | 46% | 0.40 | +10% |
| impatient traders | LSTM-AE (generic) | 2% | 14% | 5% | 29% | 0.29 | +10% |

## Resolution: does a finer view of time let the sequence detectors see the spoof?

Features computed every step instead of every 5 steps; sequence detectors read the last 24 steps.

| Detector | Spoofs 8× | Spoofs 16× | Layered 16× | Genuine flagged 16× | AUC spoof vs normal 16× | AUC spoof vs genuine 16× | False alarms |
|---|---|---|---|---|---|---|---|
| Rule | 100% | 100% | 100% | 25% | 1.00 | 1.00 | 1.4% |
| PCA (generic) | 40% | 46% | 55% | 67% | 0.63 | 0.39 | 1.4% |
| IForest (generic) | 40% | 20% | 28% | 62% | 0.45 | 0.17 | 1.1% |
| Seq-PCA (generic) | 8% | 16% | 10% | 33% | 0.54 | 0.32 | 1.7% |
| LSTM-AE (generic) | 4% | 8% | 5% | 38% | 0.52 | 0.19 | 1.7% |

Order test at 1-step resolution (AUC, intact → shuffled):

| Detector | Test | Size | AUC vs normal | AUC vs genuine |
|---|---|---|---|---|
| Seq-PCA (generic) | spoof_calm | 8× | 0.53 → 0.55 | 0.42 → 0.43 |
| Seq-PCA (generic) | layer_calm | 8× | 0.53 → 0.58 | 0.42 → 0.48 |
| Seq-PCA (generic) | spoof_calm | 16× | 0.54 → 0.56 | 0.32 → 0.16 |
| Seq-PCA (generic) | layer_calm | 16× | 0.51 → 0.49 | 0.26 → 0.13 |
| LSTM-AE (generic) | spoof_calm | 8× | 0.53 → 0.53 | 0.39 → 0.41 |
| LSTM-AE (generic) | layer_calm | 8× | 0.58 → 0.59 | 0.46 → 0.47 |
| LSTM-AE (generic) | spoof_calm | 16× | 0.52 → 0.53 | 0.19 → 0.17 |
| LSTM-AE (generic) | layer_calm | 16× | 0.49 → 0.47 | 0.16 → 0.13 |

## Orders: can an untaught detector spot the fake ORDER rather than an unusual market?

Isolation Forest trained on every order in normal sessions, described by size, lifetime, fraction filled and distance from the best price. Threshold: 1 normal order in 1,000 alerts.

| Variant | Size | AUC spoof vs genuine | AUC spoof vs normal | AUC layered vs genuine | Spoof walls flagged | Layered flagged | Genuine flagged | Normal orders flagged |
|---|---|---|---|---|---|---|---|---|
| all four features | 8× | 0.03 (0.01–0.07) | 0.97 | 0.00 | 0% | 0% | 67% | 0.08% |
| all four features | 16× | 0.00 (0.00–0.00) | 0.97 | 0.00 | 0% | 0% | 83% | 0.08% |
| without lifetime | 8× | 0.11 (0.04–0.21) | 0.99 | 0.00 | 0% | 0% | 29% | 0.11% |
| without lifetime | 16× | 0.15 (0.05–0.27) | 0.99 | 0.01 | 0% | 0% | 46% | 0.11% |
| without size | 8× | 0.00 (0.00–0.01) | 0.59 | 0.04 | 0% | 0% | 4% | 0.07% |
| without size | 16× | 0.00 (0.00–0.00) | 0.56 | 0.01 | 0% | 0% | 8% | 0.07% |
