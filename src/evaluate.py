"""Scoring rules for the experiment.

* The alert threshold for each detector is the 99th percentile of its scores on
  held-out NORMAL validation sessions, so about 1% of normal bars alert. It is
  fixed BEFORE looking at any spoofing test data and never tuned afterwards.
* An episode counts as "caught" if any bar in its window alerts.
* AUC needs no threshold at all: it is the chance that a randomly chosen episode
  scores higher than a randomly chosen comparison window (0.5 = no better than a
  coin flip, 1.0 = perfect separation).
* Confidence intervals come from bootstrapping (resampling episodes with replacement).
"""
import numpy as np

from . import config as C

EPISODE_WINDOW_BARS = 8


def threshold(validation_scores, target_fpr=C.TARGET_FPR):
    return float(np.quantile(validation_scores, 1 - target_fpr))


def caught(scores, tau, window):
    return bool((scores[window["first_bar"]:window["last_bar"] + 1] > tau).any())


def window_max(scores, window):
    return float(scores[window["first_bar"]:window["last_bar"] + 1].max())


def chance_rate(score_list, tau, window_len=EPISODE_WINDOW_BARS):
    """How often a random window of this length, in a NORMAL session, contains an alert.
    This is the "catch rate" a detector would get by pure luck."""
    hits, total = 0, 0
    for scores in score_list:
        alerts = (scores > tau).astype(int)
        csum = np.concatenate([[0], np.cumsum(alerts)])
        windows_with_alert = (csum[window_len:] - csum[:-window_len]) > 0
        hits += windows_with_alert.sum()
        total += len(windows_with_alert)
    return hits / total


def normal_window_maxes(score_list, window_len=EPISODE_WINDOW_BARS, stride=4, skip=60):
    """Max score in sliding windows of NORMAL sessions: the comparison set for AUC.
    The first `skip` bars are left out, matching how episodes never start early."""
    out = []
    for scores in score_list:
        for start in range(skip, len(scores) - window_len + 1, stride):
            out.append(scores[start:start + window_len].max())
    return np.asarray(out)


def auc(positive, negative):
    """Area under the ROC curve: the share of (positive, negative) pairs in which the
    positive scores higher, counting ties as half (the Mann-Whitney U statistic)."""
    positive = np.asarray(positive, float)
    negative = np.sort(np.asarray(negative, float))
    below = np.searchsorted(negative, positive, side="left")    # negatives strictly lower
    tied = np.searchsorted(negative, positive, side="right") - below
    return float((below + 0.5 * tied).sum() / (len(positive) * len(negative)))


def bootstrap_auc_ci(positive, negative, n_boot=400, seed=0, level=0.95):
    rng = np.random.default_rng(seed)
    positive, negative = np.asarray(positive), np.asarray(negative)
    values = [auc(rng.choice(positive, len(positive)), rng.choice(negative, len(negative)))
              for _ in range(n_boot)]
    tail = (1 - level) / 2
    return float(np.quantile(values, tail)), float(np.quantile(values, 1 - tail))


def bootstrap_ci(values, n_boot=2000, seed=0, level=0.95):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
    tail = (1 - level) / 2
    return float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail))


def paired_difference(hits_a, hits_b, n_boot=4000, seed=0, level=0.95):
    """Difference in catch rate between two detectors judged on the SAME episodes.
    Resampling episodes keeps the pairing, so the interval is much tighter than
    comparing two separate intervals. Returns (difference, ci_low, ci_high, p_two_sided)."""
    d = np.asarray(hits_a, float) - np.asarray(hits_b, float)
    rng = np.random.default_rng(seed)
    means = rng.choice(d, size=(n_boot, len(d)), replace=True).mean(axis=1)
    tail = (1 - level) / 2
    # Two-sided bootstrap p-value for "no difference".
    p = 2 * min((means <= 0).mean(), (means >= 0).mean())
    return float(d.mean()), float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail)), float(min(1.0, p))
