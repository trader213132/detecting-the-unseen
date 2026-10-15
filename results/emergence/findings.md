# Learning-agent pilot

This pilot did not establish learned spoofing.

In plain words: all 6 AI traders learned ordinary, honest ways to fill the order, and none learned to spoof. 0 of 6 final greedy policies matched the predeclared spoof-like signature. 0 had a positive extra-order effect with a pointwise 95% interval entirely above zero in the calm test market.

Training episodes: 19,200. Evaluation episodes: 8,064. Independent paired test seeds: 128.

This is a restricted execution-policy bandit, not an unrestricted sequential agent. Related work already reports learned spoofing. See the protocol for the research scope and limitations.

| Policy | Calm score | Difference vs benchmark | 95% interval | Visibility alerts |
|---|---:|---:|---|---:|
| Designed diagnostic | -0.180 | +0.214 | -0.391 to +0.646 | 100.0% |
| No fine, learner 1 | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| No fine, learner 1 (extra removed) | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| No fine, learner 1 (sampled) | -0.352 | +0.042 | -0.292 to +0.276 | 9.4% |
| No fine, learner 2 | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| No fine, learner 2 (extra removed) | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| No fine, learner 2 (sampled) | -0.305 | +0.089 | -0.060 to +0.242 | 9.4% |
| No fine, learner 3 | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| No fine, learner 3 (extra removed) | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| No fine, learner 3 (sampled) | -0.443 | -0.049 | -0.503 to +0.271 | 9.4% |
| Fine 2, learner 1 | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| Fine 2, learner 1 (extra removed) | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| Fine 2, learner 1 (sampled) | -0.292 | +0.102 | -0.031 to +0.224 | 1.6% |
| Fine 2, learner 2 | -0.393 | +0.000 | +0.000 to +0.000 | 0.0% |
| Fine 2, learner 2 (extra removed) | -0.393 | +0.000 | +0.000 to +0.000 | 0.0% |
| Fine 2, learner 2 (sampled) | -0.391 | +0.003 | -0.102 to +0.096 | 0.0% |
| Fine 2, learner 3 | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| Fine 2, learner 3 (extra removed) | -0.253 | +0.141 | +0.026 to +0.253 | 0.0% |
| Fine 2, learner 3 (sampled) | -0.302 | +0.091 | +0.000 to +0.177 | 0.8% |
| Honest benchmark | -0.393 | +0.000 | +0.000 to +0.000 | 0.0% |
| Uniform random | -0.875 | -0.482 | -1.159 to +0.018 | 7.8% |
