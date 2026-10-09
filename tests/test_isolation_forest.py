import numpy as np

from src.isolation_forest import IsolationForest, average_path_length


def test_average_path_length_matches_paper():
    assert average_path_length(np.array([1]))[0] == 0
    assert average_path_length(np.array([2]))[0] == 1
    # c(256) is about 10.24 (H(255) ~ ln(255) + 0.5772)
    assert abs(average_path_length(np.array([256]))[0] - 10.24) < 0.05


def test_outliers_score_higher_than_inliers():
    rng = np.random.default_rng(0)
    normal = rng.normal(0, 1, size=(2000, 3))
    forest = IsolationForest(n_trees=100, seed=1).fit(normal)
    inliers = rng.normal(0, 1, size=(200, 3))
    outliers = rng.normal(0, 1, size=(200, 3)) + np.array([6, 0, 0])
    assert forest.score(outliers).mean() > forest.score(inliers).mean() + 0.1
    assert (forest.score(outliers) > 0.5).mean() > 0.9


def test_scores_are_reproducible():
    X = np.random.default_rng(3).normal(size=(500, 2))
    a = IsolationForest(n_trees=20, seed=7).fit(X).score(X[:10])
    b = IsolationForest(n_trees=20, seed=7).fit(X).score(X[:10])
    assert np.allclose(a, b)
