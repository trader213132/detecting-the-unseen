# Part 5: thresholds that follow the market, and the alert budget

## Fixed vs adaptive thresholds (Part 1's detectors; trained on calm trading only)

Both versions let about 1% of calm validation bars alert. *False alerts* are per 2,000-step session (neighbouring alerting bars count once).

| Detector | Threshold | False alarms, calm | False alarms, volatile | False alerts/session, volatile | Spoofs caught 16x, calm | Spoofs caught 16x, volatile | Honest large orders flagged 16x |
|---|---|---|---|---|---|---|---|
| Rule | fixed | 0.7% | 0.7% | 2.4 | 100% | 100% | 0% |
| Rule | adaptive | 0.7% | 0.7% | 2.4 | 100% | 100% | 0% |
| PCA (generic) | fixed | 0.8% | 24.3% | 11.3 | 24% | 91% | 47% |
| PCA (generic) | adaptive | 1.1% | 8.9% | 11.9 | 34% | 42% | 47% |
| IForest (generic) | fixed | 0.7% | 11.1% | 13.9 | 12% | 61% | 23% |
| IForest (generic) | adaptive | 0.9% | 6.2% | 10.7 | 14% | 44% | 40% |
| Seq-PCA (generic) | fixed | 0.4% | 51.2% | 8.4 | 8% | 91% | 37% |
| Seq-PCA (generic) | adaptive | 0.4% | 14.4% | 6.0 | 10% | 29% | 23% |
| LSTM-AE (generic) | fixed | 0.6% | 38.8% | 9.8 | 6% | 86% | 50% |
| LSTM-AE (generic) | adaptive | 0.5% | 16.7% | 6.5 | 9% | 41% | 50% |

## The alert budget: of a desk's alerts, how many are real? (fixed thresholds, calm market)

| Detector | Spoofs caught 16x | Honest large orders flagged 16x | False alerts/session, calm | volatile | Precision, 1 spoof per session | per 10 sessions | per 100 sessions |
|---|---|---|---|---|---|---|---|
| Rule | 100% | 0% | 2.30 | 2.35 | 30% | 4% | 0% |
| PCA (generic) | 24% | 47% | 2.00 | 11.30 | 11% | 1% | 0% |
| IForest (generic) | 12% | 23% | 2.20 | 13.90 | 5% | 1% | 0% |
| Seq-PCA (generic) | 8% | 37% | 0.50 | 8.40 | 13% | 1% | 0% |
| LSTM-AE (generic) | 6% | 50% | 0.65 | 9.75 | 9% | 1% | 0% |
| Legal definition, 40-step windows | 92% | 0% | 0.70 | 0.80 | 57% | 12% | 1% |
| Legal definition, each order's life | 85% | 0% | 0.35 | 0.55 | 71% | 20% | 2% |
| Legal definition, as the market sees it | 85% | 0% | 0.25 | 0.50 | 77% | 25% | 3% |
| Both versions together | 92% | 0% | 0.90 | 1.25 | 51% | 9% | 1% |
