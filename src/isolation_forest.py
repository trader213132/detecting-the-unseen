"""Isolation Forest, written from scratch following the original paper:

    Liu, F. T., Ting, K. M. & Zhou, Z.-H. (2008). Isolation Forest. IEEE ICDM.

The idea: build many random trees. Each tree repeatedly picks a random feature
and a random split value between that feature's min and max. Unusual points
are "isolated" (end up alone in a leaf) after only a few splits, so their
average path length from the root is SHORT. Normal points sit in dense
clusters and need many splits.

Anomaly score s(x) = 2 ** (-E[h(x)] / c(psi)), where E[h(x)] is the average path
length over all trees and c(psi) is the average path length of an unsuccessful
search in a binary search tree of psi points (used to normalise). Scores near 1
mean anomalous; well below 0.5 means normal.
"""
import numpy as np

EULER_GAMMA = 0.5772156649


def average_path_length(n):
    """c(n) from the paper: expected path length for a tree built on n points."""
    n = np.asarray(n, dtype=float)
    out = np.zeros_like(n)
    big = n > 2
    out[big] = 2 * (np.log(n[big] - 1) + EULER_GAMMA) - 2 * (n[big] - 1) / n[big]
    out[n == 2] = 1.0
    return out


class IsolationForest:
    def __init__(self, n_trees=200, sample_size=256, seed=0):
        self.n_trees = n_trees
        self.sample_size = sample_size
        self.seed = seed

    def fit(self, X):
        rng = np.random.default_rng(self.seed)
        self.psi = min(self.sample_size, len(X))
        self.height_limit = int(np.ceil(np.log2(self.psi)))
        self.trees = []
        for _ in range(self.n_trees):
            sample = X[rng.choice(len(X), self.psi, replace=False)]
            self.trees.append(self._build_tree(sample, rng))
        return self

    def _build_tree(self, X, rng):
        # Each node is stored as [feature, split, left_child, right_child, n_points].
        # feature == -1 marks a leaf.
        nodes = []

        def grow(points, depth):
            index = len(nodes)
            nodes.append([-1, 0.0, -1, -1, len(points)])
            if depth >= self.height_limit or len(points) <= 1:
                return index
            spread = points.max(axis=0) - points.min(axis=0)
            candidates = np.nonzero(spread > 0)[0]
            if len(candidates) == 0:            # all points identical: can't split
                return index
            feature = rng.choice(candidates)
            low, high = points[:, feature].min(), points[:, feature].max()
            split = rng.uniform(low, high)
            goes_left = points[:, feature] < split
            left = grow(points[goes_left], depth + 1)
            right = grow(points[~goes_left], depth + 1)
            nodes[index][:4] = [feature, split, left, right]
            return index

        grow(X, 0)
        table = np.array(nodes, dtype=float)
        return {"feature": table[:, 0].astype(int), "split": table[:, 1],
                "left": table[:, 2].astype(int), "right": table[:, 3].astype(int),
                "size": table[:, 4]}

    def path_lengths(self, X):
        """Average path length of each row of X over all trees (vectorised)."""
        rows = np.arange(len(X))
        total = np.zeros(len(X))
        for tree in self.trees:
            node = np.zeros(len(X), dtype=int)
            depth = np.zeros(len(X))
            for _ in range(self.height_limit + 1):
                feature = tree["feature"][node]
                internal = feature >= 0
                if not internal.any():
                    break
                goes_left = X[rows, np.maximum(feature, 0)] < tree["split"][node]
                child = np.where(goes_left, tree["left"][node], tree["right"][node])
                node = np.where(internal, child, node)
                depth += internal
            # A leaf that still holds several points: add the expected remaining depth.
            total += depth + average_path_length(tree["size"][node])
        return total / len(self.trees)

    def score(self, X):
        return 2.0 ** (-self.path_lengths(X) / average_path_length(self.psi))
