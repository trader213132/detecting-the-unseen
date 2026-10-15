# Learning agents and detector transfer

## Question

Will a trader rewarded for execution quality learn a spoof-like configuration, and do existing detectors flag it on unseen simulated sessions?

This is a restricted replication and detector-transfer pilot, not a claim to have first discovered autonomous spoofing. David Byrd's *Learning Not to Spoof* already reports a profit-maximising RL agent learning spoofing (https://arxiv.org/abs/2306.06087). Martínez-Miranda, McBurney and Howard model manipulation through reinforcement learning in *Learning Unfair Trading* (https://arxiv.org/abs/1511.00740). Fish, Gonczarowski and Shorrer study LLM price collusion, a different mechanism (https://arxiv.org/abs/2404.00806).

## Frozen pilot design

- Existing order-book simulator, one client order per 600-step session, with 300 steps of warm-up before the earliest intervention.
- Three independent learners per condition; 100 rounds of 32 episodes each. Conditions: execution reward alone and the same reward minus two ticks per client lot for a visibility-weighted detector alert.
- Reward: cash flow plus the required final inventory valued at the arrival midpoint, divided by three client lots. Every auxiliary fill and terminal inventory adjustment counts. Reject an episode if its net inventory fails to equal the client target.
- Choose the honest benchmark (wait, improve price, cross spread) using 96 separate validation sessions per choice. Freeze it before 128 held-out test sessions.
- Four existing detectors, plus their window/visibility union. Freeze thresholds using the old normal-trading calibration data before learning. The rule measures market-wide alerts; the other scores are attributed to the learner. Their alert rates therefore have different attribution scopes.
- Evaluate each greedy policy and its no-extra-order twin on matched seeds in calm, volatile and no-feedback environments. No-feedback switches off the imbalance response of both reactive traders and market makers while retaining the same random draws.
- Evaluate the full stochastic policy too, plus a uniform random policy and an explicitly human-designed diagnostic configuration. The diagnostic control is never presented as learned behaviour.
- Report pointwise 95% paired bootstrap intervals over independent sessions, all learners, and all conditions. These exploratory intervals are not adjusted for multiple comparisons. Reusing test seeds enables paired comparisons, not additional independent observations.
- A post-hoc 0.01 / 0.1 tick per traded-lot fee sensitivity changes accounting only. It does not show how the policy would retrain under fees.

## Interpretation rules

A suspicious configuration is not proof of spoofing or intent. The predeclared signature is an opposite-side extra order of at least 8x typical size with a cancellation setting earlier than the fixed horizon. That definition can miss other strategies and does not establish that the extra order stayed unfilled or actually influenced prices.

A strong manipulation claim would require positive paired economic benefit from the extra order, evidence of a misleading displayed signal followed by withdrawal and opposite-side execution, and a credible mechanism test. Detector alerts alone cannot supply those facts. If learning converges on ordinary execution, report that negative result without claiming that other algorithms or environments cannot manipulate.

The action family is human-designed: three aggressions and an optional extra order with side, size, distance and lifetime settings. There are 843 behaviourally distinct configurations (3 no-extra choices plus 3 x 2 x 5 x 7 x 4 extra-order choices). REINFORCE learns a factorised categorical distribution with no state input. This is an execution-policy bandit, not a state-conditioned sequential trader. The simulator also deliberately contains order-book-responsive counterparties, a favourable assumption for signal manipulation. This pilot alone cannot establish unrestricted emergence, real-market profitability, novelty or general safety.

## Next evidence needed

Use a state-conditioned agent taking submit, cancel, wait and market-order primitives at each step; remove the hand-built fill-triggered cancellation option; train across independent market designs; include fees, latencies, capital limits and robust counterparties; freeze detectors before agent training; independently review held-out traces. Confirm any discovery with unseen seeds after the exploratory analysis rather than tuning until a desired story appears.

## Evidence files

`results/emergence/manifest.json` records exact configuration, source/input hashes, frozen thresholds, seeds and completion status. `training.csv` contains every learning round; `policies.json` contains every final distribution; `episodes.csv` contains every evaluation episode; `baseline_validation.csv` records baseline selection; `summary.csv` carries the paired comparisons. Existing `results/agent*` files belong to the earlier separate experiment.

## Run history

- 14 October 2026: the first run stopped after four of six learners (the computer slept). Its partial files are kept locally, not published.
- 15 October 2026: a fresh run completed training but stopped in the held-out tests when one order could not be squared up in a single step (too little liquidity to trade against). The trader now retries the square-up at market for up to 100 further steps; all 5,376 held-out orders were checked to balance exactly before rerunning.
- 15 October 2026: the reported run completed with that fix. Its source hashes are in `manifest.json`.
