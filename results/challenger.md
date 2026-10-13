# Part 4: an AI challenger

Thresholds (about 1% of normal 40-step windows alert): rule 17 lots, window 10, order-life 14, seen 13.8.

Visibility weights (share of book readings in which a price d ticks behind the best is among the 5 levels seen; 0 at the best price by design): d=0: 0.00, d=1: 1.00, d=2: 1.00, d=3: 1.00, d=4: 1.00, d=5: 0.15, d=6: 0.03, d=7: 0.01, d=8: 0.01, d=9: 0.00, d=10: 0.00, d=11: 0.00, d=12: 0.00

## The challenger's best strategy against each detector (re-tested on 40 unseen sessions)

*Payoff*: lots traded the way the spoofer wanted beyond its honest twin, per spoof, with a caught spoof's profit confiscated. *Plain* is the ordinary 16x spoof.

| Against | Strategy | Payoff (95% CI) | Gain if never caught | Caught: rule | window | order-life | seen |
|---|---|---|---|---|---|---|---|
| nobody (plain) | 16x wall, 1-2 ticks back | +0.10 (-0.24 to +0.39) | +0.10 | 100% | 89% | 78% | 78% |
| nobody (best found) | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 20% of the wall, 12 ticks back on the other side | +0.28 (+0.11 to +0.46) | +0.28 | 100% | 90% | 90% | 90% |
| rule (plain) | 16x wall, 1-2 ticks back | -0.19 (-0.46 to +0.00) | +0.10 | 100% | 89% | 78% | 78% |
| rule (best found) | 12x wall, 2 ticks back, in 3 layers | +0.25 (+0.09 to +0.45) | +0.25 | 0% | 90% | 90% | 90% |
| window (plain) | 16x wall, 1-2 ticks back | -0.19 (-0.46 to +0.00) | +0.10 | 100% | 89% | 78% | 78% |
| window (best found) | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 70% of the wall, 12 ticks back on the other side | +0.28 (+0.11 to +0.46) | +0.28 | 100% | 0% | 0% | 90% |
| order-life (plain) | 16x wall, 1-2 ticks back | -0.15 (-0.44 to +0.05) | +0.10 | 100% | 89% | 78% | 78% |
| order-life (best found) | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 70% of the wall, 12 ticks back on the other side | +0.28 (+0.11 to +0.46) | +0.28 | 100% | 0% | 0% | 90% |
| seen (plain) | 16x wall, 1-2 ticks back | -0.15 (-0.44 to +0.05) | +0.10 | 100% | 89% | 78% | 78% |
| seen (best found) | 5x wall, 3 ticks back, in 4 layers, decoy 10% of the wall, 7 ticks back on the other side | +0.12 (+0.03 to +0.26) | +0.12 | 0% | 85% | 0% | 8% |

## Honest trading and standard spoofs

| Case | Size | Detector | Value | n |
|---|---|---|---|---|
| normal calm market (false alarms (share of 40-step windows)) |  | order-life | 0.7% | 20 |
| normal calm market (false alarms (share of 40-step windows)) |  | seen | 0.6% | 20 |
| normal volatile market (false alarms (share of 40-step windows)) |  | order-life | 1.3% | 20 |
| normal volatile market (false alarms (share of 40-step windows)) |  | seen | 1.2% | 20 |
| honest large order (flagged) | 8x | rule | 16.7% | 30 |
| honest large order (flagged) | 8x | window | 0.0% | 30 |
| honest large order (flagged) | 8x | order-life | 0.0% | 30 |
| honest large order (flagged) | 8x | seen | 0.0% | 30 |
| honest large order (flagged) | 16x | rule | 13.3% | 30 |
| honest large order (flagged) | 16x | window | 0.0% | 30 |
| honest large order (flagged) | 16x | order-life | 0.0% | 30 |
| honest large order (flagged) | 16x | seen | 0.0% | 30 |
| honest quick cancel (flagged) | 8x | rule | 93.3% | 60 |
| honest quick cancel (flagged) | 8x | window | 0.0% | 60 |
| honest quick cancel (flagged) | 8x | order-life | 0.0% | 60 |
| honest quick cancel (flagged) | 8x | seen | 0.0% | 60 |
| honest quick cancel (flagged) | 16x | rule | 100.0% | 60 |
| honest quick cancel (flagged) | 16x | window | 0.0% | 60 |
| honest quick cancel (flagged) | 16x | order-life | 0.0% | 60 |
| honest quick cancel (flagged) | 16x | seen | 0.0% | 60 |
| honest change of mind (flagged) | 8x | rule | 93.3% | 60 |
| honest change of mind (flagged) | 8x | window | 88.3% | 60 |
| honest change of mind (flagged) | 8x | order-life | 88.3% | 60 |
| honest change of mind (flagged) | 8x | seen | 88.3% | 60 |
| honest change of mind (flagged) | 16x | rule | 98.3% | 60 |
| honest change of mind (flagged) | 16x | window | 91.7% | 60 |
| honest change of mind (flagged) | 16x | order-life | 91.7% | 60 |
| honest change of mind (flagged) | 16x | seen | 91.7% | 60 |
| market maker working off a position (flagged) | 8x | rule | 96.7% | 60 |
| market maker working off a position (flagged) | 8x | window | 100.0% | 60 |
| market maker working off a position (flagged) | 8x | order-life | 98.3% | 60 |
| market maker working off a position (flagged) | 8x | seen | 0.0% | 60 |
| market maker working off a position (flagged) | 16x | rule | 100.0% | 60 |
| market maker working off a position (flagged) | 16x | window | 100.0% | 60 |
| market maker working off a position (flagged) | 16x | order-life | 98.3% | 60 |
| market maker working off a position (flagged) | 16x | seen | 0.0% | 60 |
| spoof (caught) | 8x | rule | 100.0% | 80 |
| spoof (caught) | 8x | window | 81.2% | 80 |
| spoof (caught) | 8x | order-life | 71.2% | 80 |
| spoof (caught) | 8x | seen | 71.2% | 80 |
| spoof (caught) | 16x | rule | 100.0% | 80 |
| spoof (caught) | 16x | window | 92.5% | 80 |
| spoof (caught) | 16x | order-life | 85.0% | 80 |
| spoof (caught) | 16x | seen | 85.0% | 80 |
| layered spoof (caught) | 8x | rule | 0.0% | 60 |
| layered spoof (caught) | 8x | window | 85.0% | 60 |
| layered spoof (caught) | 8x | order-life | 85.0% | 60 |
| layered spoof (caught) | 8x | seen | 85.0% | 60 |
| layered spoof (caught) | 16x | rule | 5.0% | 60 |
| layered spoof (caught) | 16x | window | 85.0% | 60 |
| layered spoof (caught) | 16x | order-life | 85.0% | 60 |
| layered spoof (caught) | 16x | seen | 85.0% | 60 |
