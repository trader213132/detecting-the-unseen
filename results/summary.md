# Results summary

All numbers come from simulated markets and synthetic spoofing. They describe how the detectors behave in this controlled setting, NOT real-world surveillance performance. Brackets are 95% bootstrap confidence intervals. Every detector was trained on normal calm sessions only unless stated otherwise.

Detectors: **Rule** (large order cancelled quickly; hand-written), **PCA** and **IForest** (one 5-step bar at a time), **Seq-PCA** and **LSTM-AE** (a window of the last 8 bars, so they can see the order of events). *generic* = 18 standard order-book features; *informed* = plus 6 features chosen because we know what spoofing looks like.

## 1. Spoofs caught vs genuine large orders flagged (calm market)

Threshold: about 1% of normal bars alert. An episode is caught if any bar in its 8-bar window alerts.

| Detector | Spoofs, 4× | Spoofs, 8× | Spoofs, 16× | Layered, 16× | Genuine flagged, 8× | Genuine flagged, 16× | Chance |
|---|---|---|---|---|---|---|---|
| Rule | 8% (2%–14%) | 100% (100%–100%) | 100% (100%–100%) | 8% (2%–17%) | 7% (0%–17%) | 0% (0%–0%) | 6% |
| PCA (generic) | 1% (0%–4%) | 6% (1%–11%) | 24% (15%–34%) | 15% (7%–25%) | 7% (0%–17%) | 47% (30%–63%) | 6% |
| PCA (informed) | 9% (2%–15%) | 38% (28%–48%) | 98% (94%–100%) | 8% (2%–15%) | 23% (10%–40%) | 90% (80%–100%) | 6% |
| IForest (generic) | 8% (2%–14%) | 10% (4%–16%) | 12% (6%–20%) | 23% (13%–33%) | 7% (0%–17%) | 23% (10%–40%) | 6% |
| IForest (informed) | 4% (0%–9%) | 15% (8%–22%) | 14% (8%–21%) | 22% (12%–33%) | 17% (7%–30%) | 33% (17%–50%) | 8% |
| Seq-PCA (generic) | 5% (1%–10%) | 1% (0%–4%) | 8% (2%–14%) | 13% (5%–23%) | 10% (0%–23%) | 37% (20%–53%) | 2% |
| LSTM-AE (generic) | 1% (0%–4%) | 6% (1%–11%) | 9% (4%–15%) | 17% (8%–25%) | 10% (0%–23%) | 50% (33%–67%) | 3% |

## 2. Can a detector tell a spoof from an honest order of the same size? (AUC)

AUC needs no threshold: 0.50 means the detector cannot tell the two apart; 1.00 means it separates them perfectly. 'vs normal' compares spoof episodes with ordinary 8-bar stretches.

| Detector | Spoof vs normal, 16× | Spoof vs genuine, 8× | Spoof vs genuine, 16× | Layered vs genuine, 16× |
|---|---|---|---|---|
| Rule | 1.00 (1.00–1.00) | 1.00 (1.00–1.00) | 1.00 (1.00–1.00) | 0.85 (0.75–0.94) |
| PCA (generic) | 0.85 (0.82–0.89) | 0.50 (0.37–0.65) | 0.44 (0.32–0.57) | 0.26 (0.18–0.37) |
| PCA (informed) | 0.99 (0.98–0.99) | 0.64 (0.50–0.75) | 0.47 (0.35–0.62) | 0.05 (0.01–0.11) |
| IForest (generic) | 0.65 (0.60–0.70) | 0.43 (0.31–0.54) | 0.32 (0.21–0.43) | 0.53 (0.39–0.67) |
| IForest (informed) | 0.74 (0.70–0.79) | 0.49 (0.36–0.64) | 0.35 (0.24–0.47) | 0.39 (0.28–0.51) |
| Seq-PCA (generic) | 0.74 (0.68–0.79) | 0.43 (0.31–0.55) | 0.31 (0.21–0.42) | 0.27 (0.18–0.39) |
| LSTM-AE (generic) | 0.71 (0.66–0.76) | 0.41 (0.29–0.52) | 0.14 (0.07–0.22) | 0.26 (0.16–0.36) |

## 3. The order test: do the sequence detectors use the order of events?

Each window is scored again with its bars in a random order. If results barely change, the detector is not really using the order.

| Detector | Test | Size | Caught (intact → shuffled) | AUC vs genuine (intact → shuffled) |
|---|---|---|---|---|
| Seq-PCA (generic) | spoof | 8× | 1% → 35% | 0.43 → 0.43 |
| Seq-PCA (generic) | layer | 8× | 3% → 30% | 0.35 → 0.35 |
| Seq-PCA (generic) | spoof | 16× | 8% → 52% | 0.31 → 0.27 |
| Seq-PCA (generic) | layer | 16× | 13% → 47% | 0.27 → 0.26 |
| LSTM-AE (generic) | spoof | 8× | 6% → 8% | 0.41 → 0.42 |
| LSTM-AE (generic) | layer | 8× | 5% → 5% | 0.35 → 0.35 |
| LSTM-AE (generic) | spoof | 16× | 9% → 12% | 0.14 → 0.14 |
| LSTM-AE (generic) | layer | 16× | 17% → 27% | 0.26 → 0.26 |

## 4. Paired comparisons (same episodes, calm market)

Difference in catch rate (A − B) with a paired bootstrap interval and two-sided p-value.

| A | B | Test | Size | A | B | A − B (95% CI) | p |
|---|---|---|---|---|---|---|---|
| Seq-PCA (generic) | PCA (generic) | spoof | 8× | 1% | 6% | -5 pts (-10 to -1) | 0.035 |
| Seq-PCA (generic) | PCA (generic) | spoof | 16× | 8% | 24% | -16 pts (-26 to -6) | 0.003 |
| Seq-PCA (generic) | PCA (generic) | layer | 8× | 3% | 5% | -2 pts (-8 to +5) | 0.806 |
| Seq-PCA (generic) | PCA (generic) | layer | 16× | 13% | 15% | -2 pts (-13 to +8) | 0.866 |
| Seq-PCA (generic) | PCA (generic) | control | 8× | 10% | 7% | +3 pts (-7 to +13) | 0.773 |
| Seq-PCA (generic) | PCA (generic) | control | 16× | 37% | 47% | -10 pts (-30 to +10) | 0.453 |
| LSTM-AE (generic) | IForest (generic) | spoof | 8× | 6% | 10% | -4 pts (-11 to +4) | 0.404 |
| LSTM-AE (generic) | IForest (generic) | spoof | 16× | 9% | 12% | -4 pts (-12 to +5) | 0.493 |
| LSTM-AE (generic) | IForest (generic) | layer | 8× | 5% | 7% | -2 pts (-10 to +5) | 0.814 |
| LSTM-AE (generic) | IForest (generic) | layer | 16× | 17% | 23% | -7 pts (-18 to +5) | 0.311 |
| LSTM-AE (generic) | IForest (generic) | control | 8× | 10% | 7% | +3 pts (-7 to +13) | 0.787 |
| LSTM-AE (generic) | IForest (generic) | control | 16× | 50% | 23% | +27 pts (+10 to +43) | 0.005 |
| LSTM-AE (generic) | Seq-PCA (generic) | spoof | 8× | 6% | 1% | +5 pts (+1 to +10) | 0.035 |
| LSTM-AE (generic) | Seq-PCA (generic) | spoof | 16× | 9% | 8% | +1 pts (-5 to +8) | 0.863 |
| LSTM-AE (generic) | Seq-PCA (generic) | layer | 8× | 5% | 3% | +2 pts (-5 to +8) | 0.820 |
| LSTM-AE (generic) | Seq-PCA (generic) | layer | 16× | 17% | 13% | +3 pts (-5 to +13) | 0.578 |
| LSTM-AE (generic) | Seq-PCA (generic) | control | 8× | 10% | 10% | +0 pts (-10 to +10) | 1.000 |
| LSTM-AE (generic) | Seq-PCA (generic) | control | 16× | 50% | 37% | +13 pts (-3 to +30) | 0.183 |
| LSTM-AE (generic) | Rule | spoof | 8× | 6% | 100% | -94 pts (-99 to -89) | 0.000 |
| LSTM-AE (generic) | Rule | spoof | 16× | 9% | 100% | -91 pts (-96 to -85) | 0.000 |
| LSTM-AE (generic) | Rule | layer | 8× | 5% | 7% | -2 pts (-8 to +5) | 0.825 |
| LSTM-AE (generic) | Rule | layer | 16× | 17% | 8% | +8 pts (-2 to +18) | 0.152 |
| LSTM-AE (generic) | Rule | control | 8× | 10% | 7% | +3 pts (-10 to +17) | 0.838 |
| LSTM-AE (generic) | Rule | control | 16× | 50% | 0% | +50 pts (+33 to +67) | 0.000 |
| Rule | PCA (informed) | spoof | 8× | 100% | 38% | +62 pts (+52 to +72) | 0.000 |
| Rule | PCA (informed) | spoof | 16× | 100% | 98% | +2 pts (+0 to +6) | 0.255 |
| Rule | PCA (informed) | layer | 8× | 7% | 12% | -5 pts (-15 to +7) | 0.452 |
| Rule | PCA (informed) | layer | 16× | 8% | 8% | +0 pts (-10 to +8) | 1.000 |
| Rule | PCA (informed) | control | 8× | 7% | 23% | -17 pts (-33 to +0) | 0.059 |
| Rule | PCA (informed) | control | 16× | 0% | 90% | -90 pts (-100 to -80) | 0.000 |

## 5. False alarms when the market regime changes

Share of bars in NORMAL test sessions (no spoofing) that raise an alert. Target: 1%.

| Detector | Calm → calm | Calm → volatile | Calm+volatile → calm | Calm+volatile → volatile |
|---|---|---|---|---|
| Rule | 0.7% | 0.8% | 0.7% | 0.8% |
| PCA (generic) | 0.9% | 24.1% | 0.2% | 1.8% |
| PCA (informed) | 1.1% | 15.7% | 0.3% | 1.5% |
| IForest (generic) | 1.0% | 11.0% | 0.0% | 2.0% |
| IForest (informed) | 1.2% | 12.7% | 0.0% | 2.0% |
| Seq-PCA (generic) | 0.5% | 50.9% | 0.0% | 1.5% |
| LSTM-AE (generic) | 1.0% | 40.1% | 0.0% | 2.1% |

## 6. Spoofs caught in a VOLATILE market (16×), with chance levels

| Detector | Trained calm only | (chance) | Trained calm+volatile | (chance) |
|---|---|---|---|---|
| Rule | 100% (100%–100%) | 6% | 100% (100%–100%) | 6% |
| PCA (generic) | 91% (85%–96%) | 79% | 61% (50%–71%) | 12% |
| PCA (informed) | 100% (100%–100%) | 64% | 48% (36%–59%) | 8% |
| IForest (generic) | 61% (50%–71%) | 52% | 14% (6%–22%) | 13% |
| IForest (informed) | 79% (69%–88%) | 59% | 25% (16%–34%) | 13% |
| Seq-PCA (generic) | 91% (84%–98%) | 79% | 2% (0%–6%) | 4% |
| LSTM-AE (generic) | 86% (79%–94%) | 67% | 14% (8%–21%) | 6% |

## 7. Which spoof-informed feature does the teaching? (PCA, calm market)

| PCA variant | Spoofs caught, 8× | Spoofs caught, 16× | Layered, 16× | Genuine flagged, 16× | AUC spoof vs genuine, 16× |
|---|---|---|---|---|---|
| all informed features | 38% | 98% | 8% | 90% | 0.47 |
| without max_add | 31% | 92% | 12% | 40% | 0.83 |
| without max_fast_cancel | 21% | 79% | 8% | 97% | 0.34 |
| without big_add_distance | 29% | 95% | 7% | 90% | 0.50 |
| without imbalance | 25% | 94% | 7% | 83% | 0.49 |
| without imbalance_change | 11% | 60% | 13% | 90% | 0.23 |
| without signed_flow | 15% | 68% | 8% | 93% | 0.22 |
| generic only | 6% | 24% | 15% | 47% | 0.44 |

## 8. Does the spoofing actually work? (calm market, spoof vs honest twin)

| Spoof | Size | Price shift in spoofer's favour (ticks) | Extra chance the genuine order fills | Filled with wall | Filled without |
|---|---|---|---|---|---|
| single wall | 1× | -0.00 (-0.05 to +0.04) | +2 pts (-2 to +8) | 74% | 71% |
| single wall | 2× | +0.01 (-0.03 to +0.05) | +1 pts (+0 to +4) | 70% | 69% |
| single wall | 4× | +0.05 (+0.01 to +0.09) | -2 pts (-6 to +0) | 69% | 71% |
| single wall | 8× | +0.11 (+0.05 to +0.18) | +12 pts (+6 to +20) | 81% | 69% |
| single wall | 16× | +0.12 (+0.00 to +0.21) | +16 pts (+8 to +25) | 90% | 74% |
| layered | 1× | +0.06 (+0.02 to +0.11) | +7 pts (+0 to +15) | 68% | 62% |
| layered | 2× | +0.05 (-0.03 to +0.12) | -2 pts (-8 to +3) | 57% | 58% |
| layered | 4× | +0.04 (-0.03 to +0.10) | +2 pts (-3 to +7) | 77% | 75% |
| layered | 8× | +0.12 (+0.07 to +0.18) | +15 pts (+7 to +23) | 85% | 70% |
| layered | 16× | +0.14 (+0.06 to +0.23) | +8 pts (+2 to +15) | 85% | 77% |
