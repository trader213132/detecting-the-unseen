# Part 3: the price of evasion

Each row is one way a spoofer could try to dodge the principle detector. *Extra lots* is how many more lots the spoofer traded the way it wanted than its honest twin (same session, no wall): the benefit of spoofing. Thresholds: principle detector 10 lots (40-step windows), 17 lots (160-step windows) and 14 lots (each order's own life), rule 17 lots; each lets about 1% of normal trading alert.

| Strategy | Size | Extra lots vs honest twin (95% CI) | Caught: principle, 40 steps | Caught: principle, 160 steps | Caught: principle, order life | Caught: rule | Wall lots that really traded | Buy-back cost (ticks/lot) |
|---|---|---|---|---|---|---|---|---|
| no evasion | 8× | +0.38 (+0.19 to +0.59) | 81% | 81% | 71% | 100% | 0.1 |  |
| patient: 15 steps | 8× | +0.38 (+0.19 to +0.59) | 76% | 79% | 68% | 99% | 0.3 |  |
| patient: 40 steps | 8× | +0.35 (+0.16 to +0.56) | 29% | 78% | 66% | 95% | 0.4 |  |
| patient: 80 steps | 8× | +0.38 (+0.19 to +0.59) | 30% | 78% | 66% | 64% | 0.4 |  |
| patient: 160 steps | 8× | +0.38 (+0.19 to +0.59) | 30% | 50% | 66% | 62% | 0.3 |  |
| buys back 1 of 3 lots | 8× | -0.46 (-0.66 to -0.24) | 79% | 79% | 70% | 100% | 0.1 | +0.66 |
| buys back 2 of 3 lots | 8× | -1.16 (-1.40 to -0.90) | 79% | 79% | 70% | 100% | 0.1 | +0.66 |
| buys back all 3 lots | 8× | -1.79 (-2.11 to -1.44) | 18% | 19% | 15% | 100% | 0.1 | +0.66 |
| no evasion | 16× | +0.41 (+0.17 to +0.66) | 92% | 92% | 85% | 100% | 0.1 |  |
| patient: 15 steps | 16× | +0.44 (+0.21 to +0.68) | 91% | 92% | 84% | 100% | 0.1 |  |
| patient: 40 steps | 16× | +0.44 (+0.21 to +0.68) | 29% | 90% | 81% | 91% | 0.3 |  |
| patient: 80 steps | 16× | +0.44 (+0.21 to +0.68) | 30% | 90% | 82% | 52% | 0.3 |  |
| patient: 160 steps | 16× | +0.40 (+0.15 to +0.65) | 26% | 51% | 78% | 59% | 0.5 |  |
| buys back 1 of 3 lots | 16× | -0.49 (-0.72 to -0.25) | 92% | 92% | 86% | 100% | 0.1 | +0.83 |
| buys back 2 of 3 lots | 16× | -1.31 (-1.55 to -1.06) | 92% | 92% | 85% | 100% | 0.1 | +0.81 |
| buys back all 3 lots | 16× | -2.04 (-2.31 to -1.75) | 24% | 24% | 20% | 100% | 0.1 | +0.82 |

The order-life version on honest trading:

| Test | Value | n |
|---|---|---|
| false alarms, normal calm market (share of 40-step windows) | 0.7% | 20 |
| false alarms, normal volatile market (share of 40-step windows) | 1.3% | 20 |
| honest large orders flagged, 16x | 0.0% | 30 |
| honest quick withdrawals flagged, 16x | 0.0% | 60 |
| honest changes of mind flagged, 16x | 91.7% | 60 |
