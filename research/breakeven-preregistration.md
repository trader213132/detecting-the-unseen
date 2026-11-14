# Break-even pilot: pre-registration

**Status:** frozen before any pilot session was run (14 November 2026). The SHA-256 fingerprint of this file is
published in `research/breakeven-seal.txt` and on the website. Changing a single character changes the
fingerprint.

**Scope.** This is a *pilot* for the Economics proposal "When Does Market Manipulation Pay?". It runs on
**development seeds only**. The held-out seeds and reserved market cells below are **not run** in the pilot. They
are kept for the real test.

**AI assistance.** An AI assistant wrote this protocol and the pilot code at the student's direction. The model,
the choice of conditions and the interpretation are the student's responsibility.

## 1. The model

For one spoof attempt, against its honest twin (the same seed and the same genuine order, with no wall):

    net payoff  =  G  −  U  −  C  −  p·F

| Term | Measured how (pilot) | Unit |
|---|---|---|
| **G** | extra lots of the genuine order that traded, vs the honest twin | lots |
| **U** | lots of the spoofer's own wall that really traded (unwanted fills) | lots |
| **C** | extra fees. **The simulator charges none, so C = 0** (stated, not hidden) | lots-equivalent |
| **p** | share of attempts the detector flags, at a threshold where about 1% of normal 40-step blocks in *that same market* alert | probability |
| **F** | hypothetical sanction, an **experimental parameter**, not an estimate of any real fine | lots-equivalent |

Break-even sanction: **F\* = (G − U − C) / p**. Above F\*, the expected payoff is negative. If G − U − C ≤ 0, the
attempt does not pay even with no penalty (F\* = 0).

Unit convention: one lot of the genuine order traded is worth 1 model unit. This is a simplification. The pilot
measures *how much more the spoofer trades*, not the price it trades at.

## 2. Conditions (the grid)

Development cells: **3 × 4 × 2 = 24**

| Factor | Simulator setting | Development values | Reserved (not run) |
|---|---|---|---|
| Liquidity | `arrival_rate` (traders per step) | 1.0, 1.5, 2.25 | 1.25, 1.85 |
| Book responsiveness | `react_shift`; `react_bias` and `mm_react_shift` scale in proportion (×react_shift/6) | 0, 3, 6, 9 | 4.5 |
| Volatility | regime | calm, volatile | — |

Reserved cells for the transfer test: {1.25, 1.85} × {4.5} × {calm, volatile} = **4 cells**.

Strategies: a single-price wall of **8×** and of **16×** typical order size (the plain spoof of the earlier study).

## 3. Seeds

| Use | Seeds | Run in pilot? |
|---|---|---|
| Development (spoof and honest twin) | 90 000 – 90 059 (60 sessions, 2 attempts each) | yes |
| Threshold calibration (normal trading, per cell) | 93 000 – 93 019 | yes |
| **Held-out test** | 91 000 – 91 059 | **no: sealed** |
| **Reserved-cell test** | 92 000 – 92 059 | **no: sealed** |

## 4. Detectors

- **Rule**: largest fast cancellation in a bar (the original simple rule).
- **Order-life (law-informed)**: the principle detector scored over each withdrawn order's own life.

Each detector's threshold is re-calibrated in every cell on that cell's normal trading, so about 1% of normal 40-step
blocks alert. A regulator would calibrate on the market it watches.

## 5. Outputs of the pilot

For each development cell and wall size: mean G, U and net = G − U (with 95% bootstrap intervals over sessions), p
for each detector, and F\* = max(net, 0) / p.

## 6. Frozen predictions (written after the pilot, sealed before any test)

After the pilot, `research/breakeven-predictions.json` will record:

1. For every development cell: the predicted net payoff (the pilot mean), its 95% interval, and the predicted p.
2. For every reserved cell: the predicted net payoff from a linear model fitted on the development cells only
   (net ~ arrival + responsiveness + volatile + responsiveness×volatile, separately per wall size).

That file's SHA-256 is also sealed in `research/breakeven-seal.txt`.

## 7. Success criteria for the future test (decided now)

On the held-out seeds:

- **Direction:** the sign of the net payoff (positive / not positive, judged by whether the 95% interval excludes 0)
  agrees with the prediction in **at least 80% of cells**.
- **Size:** the held-out cell mean lies inside the pilot's 95% interval in **at least 80% of cells**.
- **Deterrence:** for the order-life detector, the held-out p lies within ±0.10 of the predicted p in at least 80% of
  cells.

On the reserved cells: the predicted sign is right in **at least 3 of 4** cells per wall size.

All outcomes will be reported, including failures. If the model is revised after seeing test results, a new untouched
test set is needed.

## 8. What this pilot cannot show

- Real markets: these are simulated traders.
- Intent: an alert is not proof of intent.
- Real enforcement: F is a scenario, and real detection rates are unknown.
- Best honest alternative: the twin waits passively. The earlier learning pilot found an honest "step in front"
  strategy that captures much of the benefit, so the true incentive vs the *best* honest option is likely
  smaller than G here.
