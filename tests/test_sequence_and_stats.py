import numpy as np
import pandas as pd
import pytest

from src.detectors import LSTMAEDetector, SeqPCADetector, make_windows, shuffle_windows
from src.evaluate import auc, normal_window_maxes, paired_difference


def test_windows_only_look_backwards():
    X = np.arange(10, dtype=float).reshape(5, 2)          # bar t has values [2t, 2t+1]
    W = make_windows(X, 3)
    assert W.shape == (5, 3, 2)
    assert np.array_equal(W[4], X[2:5])                    # window for bar 4 = bars 2, 3, 4
    assert np.array_equal(W[0], np.repeat(X[:1], 3, axis=0))   # padded with bar 0, never the future


def test_shuffle_keeps_the_same_bars():
    rng = np.random.default_rng(0)
    W = rng.normal(size=(50, 8, 3))
    S = shuffle_windows(W, np.random.default_rng(1))
    assert np.allclose(np.sort(W, axis=1), np.sort(S, axis=1))     # same bars in each window
    assert not np.allclose(W, S)                                    # but in a different order


def test_auc_matches_brute_force():
    rng = np.random.default_rng(3)
    pos, neg = rng.normal(1, 1, 40).round(1), rng.normal(0, 1, 60).round(1)    # rounding makes ties
    brute = np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg])
    assert auc(pos, neg) == pytest.approx(brute)
    assert auc([3, 4], [1, 2]) == 1.0 and auc([1, 2], [3, 4]) == 0.0 and auc([1], [1]) == 0.5


def test_paired_difference_is_zero_for_identical_detectors():
    hits = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=float)
    diff, low, high, p = paired_difference(hits, hits)
    assert diff == 0 and low == 0 and high == 0 and p == 1.0
    diff, low, high, p = paired_difference(np.ones(40), np.zeros(40))
    assert diff == 1 and p < 0.01


def test_normal_window_maxes_counts_windows():
    scores = [np.arange(100.0)]
    maxes = normal_window_maxes(scores, window_len=8, stride=4, skip=60)
    assert len(maxes) == len(range(60, 93, 4)) and maxes[0] == 67


def _toy_frames(n_sessions, rng, columns):
    # A smooth normal pattern: each feature is a slow sine wave plus noise.
    frames = []
    for _ in range(n_sessions):
        t = np.arange(120)
        data = {c: np.sin(t / 7 + i) + 0.1 * rng.normal(size=t.size) for i, c in enumerate(columns)}
        frames.append(pd.DataFrame(data))
    return frames


@pytest.mark.parametrize("make", [
    lambda cols: SeqPCADetector(cols, "toy", width=6),
    lambda cols: LSTMAEDetector(cols, "toy", width=6, hidden=16, latent=4, epochs=6, batch_size=64),
])
def test_sequence_detectors_flag_a_broken_pattern(make):
    pytest.importorskip("torch")
    rng = np.random.default_rng(0)
    columns = ["a", "b", "c"]
    det = make(columns).fit(_toy_frames(20, rng, columns))
    test = _toy_frames(1, rng, columns)[0]
    test.loc[60:63, "a"] += 4.0                            # a sudden burst the normal data never has
    scores = det.score(test)
    assert scores.shape == (len(test),)
    assert scores[60:70].max() > np.quantile(scores[:55], 0.95)
