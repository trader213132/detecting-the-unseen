# Part 6: the price of a false alarm

The best payoff with no surveillance at all (chosen on practice sessions, measured on unseen ones): +0.28 lots per spoof.

| Detector | False alarms (share of 40-step blocks) | Best payoff a spoofer keeps | Its strategy |
|---|---|---|---|
| rule | 0.0% | +0.10 | 16x wall, 1 ticks back, in 2 layers |
| rule | 0.5% | +0.11 | 16x wall, 1-2 ticks back, in 4 layers |
| rule | 1.0% | +0.11 | 16x wall, 1-2 ticks back, in 4 layers |
| rule | 2.4% | +0.11 | 16x wall, 1-2 ticks back, in 4 layers |
| rule | 5.6% | +0.11 | 16x wall, 1-2 ticks back, in 4 layers |
| window | 0.0% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 40% of the wall, 12 ticks back on the other side |
| window | 0.4% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 70% of the wall, 12 ticks back on the other side |
| window | 1.0% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 70% of the wall, 12 ticks back on the other side |
| window | 2.0% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 70% of the wall, 12 ticks back on the other side |
| window | 5.2% | +0.28 | 13x wall, 2 ticks back, decoy 140% of the wall, 7 ticks back on the other side |
| order-life | 0.0% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 20% of the wall, 12 ticks back on the other side |
| order-life | 0.5% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 70% of the wall, 12 ticks back on the other side |
| order-life | 1.0% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 70% of the wall, 12 ticks back on the other side |
| order-life | 1.8% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 70% of the wall, 12 ticks back on the other side |
| order-life | 6.0% | +0.28 | 13x wall, 2 ticks back, decoy 140% of the wall, 7 ticks back on the other side |
| seen | 0.0% | +0.28 | 12x wall, 3 ticks back, kept 1 step after the trade, decoy 20% of the wall, 12 ticks back on the other side |
| seen | 0.6% | +0.11 | 4x wall, 3 ticks back, decoy 130% of the wall, 12 ticks back on the other side |
| seen | 1.1% | -0.10 | 14x wall, 4 ticks back, in 2 layers, kept 40 steps after the trade, decoy 150% of the wall, 6 ticks back on the other side |
| seen | 2.1% | -0.10 | 14x wall, 4 ticks back, in 2 layers, kept 40 steps after the trade, decoy 150% of the wall, 6 ticks back on the other side |
| seen | 4.6% | -0.10 | 14x wall, 4 ticks back, in 2 layers, kept 40 steps after the trade, decoy 150% of the wall, 6 ticks back on the other side |
