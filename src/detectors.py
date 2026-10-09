"""The detectors. Every one of them is fitted on NORMAL sessions only; none ever sees
a spoofing example. Each gives an anomaly score per bar (higher = more unusual).

One bar at a time:
  RuleDetector       Traditional surveillance: "a large order cancelled quickly".
                     This is pure domain knowledge, with no learning at all.
  PCADetector        Learns the main patterns of normal bars. Score = how badly a bar
                     is rebuilt from those patterns (a linear autoencoder).
  IForestDetector    Isolation Forest: score = how easily random splits isolate the bar.

A window of the last W bars (they can see the ORDER of events):
  SeqPCADetector     PCA on the whole window, flattened.
  LSTMAEDetector     An LSTM autoencoder: a recurrent neural network squeezes the window
                     into a few numbers and rebuilds it. Score = rebuild error.

fit() takes a list of per-session feature tables, so windows never cross from one
session into another. Sequence detectors accept a `shuffle` random generator in
score(): it scrambles the bar order inside every window (the order test).
"""
import numpy as np
import pandas as pd

from .features import LOG_FEATURES
from .isolation_forest import IsolationForest


class Standardiser:
    """log1p heavy-tailed columns, then z-score using statistics from TRAINING data only."""

    def __init__(self, columns):
        self.columns = columns

    def _raw(self, frame):
        X = frame[self.columns].to_numpy(dtype=float).copy()
        for j, name in enumerate(self.columns):
            if name in LOG_FEATURES:
                X[:, j] = np.log1p(np.maximum(X[:, j], 0))
        return X

    def fit(self, frame):
        X = self._raw(frame)
        self.mean = X.mean(axis=0)
        self.std = np.maximum(X.std(axis=0), 1e-6)
        return self

    def transform(self, frame):
        return (self._raw(frame) - self.mean) / self.std


def make_windows(X, width):
    """(n_bars, d) -> (n_bars, width, d). Window t holds bars t-width+1 .. t, so the
    score for bar t only uses the past. The first bars are padded with bar 0."""
    padded = np.vstack([np.repeat(X[:1], width - 1, axis=0), X])
    index = np.arange(len(X))[:, None] + np.arange(width)[None, :]
    return padded[index]


def shuffle_windows(windows, rng):
    """Randomly reorder the bars inside each window (same bars, scrambled order)."""
    order = np.argsort(rng.random(windows.shape[:2]), axis=1)
    return np.take_along_axis(windows, order[:, :, None], axis=1)


def _stack(frames):
    return frames if isinstance(frames, pd.DataFrame) else pd.concat(frames, ignore_index=True)


# --- One bar at a time --------------------------------------------------------
class RuleDetector:
    def __init__(self):
        self.name = "Rule"

    def fit(self, frames):
        return self

    def score(self, frame, shuffle=None):
        return frame["max_fast_cancel"].to_numpy(dtype=float)


class PCADetector:
    def __init__(self, columns, label, variance_kept=0.90):
        self.columns, self.variance_kept = columns, variance_kept
        self.name = f"PCA ({label})"

    def fit(self, frames):
        train = _stack(frames)
        self.scaler = Standardiser(self.columns).fit(train)
        X = self.scaler.transform(train)
        _, singular_values, components = np.linalg.svd(X, full_matrices=False)
        explained = np.cumsum(singular_values ** 2) / np.sum(singular_values ** 2)
        k = int(np.searchsorted(explained, self.variance_kept) + 1)
        self.components = components[:k]
        return self

    def score(self, frame, shuffle=None):
        X = self.scaler.transform(frame)
        reconstruction = X @ self.components.T @ self.components
        return ((X - reconstruction) ** 2).sum(axis=1)


class IForestDetector:
    def __init__(self, columns, label, seed=0):
        self.columns, self.seed = columns, seed
        self.name = f"IForest ({label})"

    def fit(self, frames):
        train = _stack(frames)
        self.scaler = Standardiser(self.columns).fit(train)
        self.forest = IsolationForest(n_trees=200, sample_size=256, seed=self.seed)
        self.forest.fit(self.scaler.transform(train))
        return self

    def score(self, frame, shuffle=None):
        return self.forest.score(self.scaler.transform(frame))


# --- A window of bars ---------------------------------------------------------
class _WindowDetector:
    width = 8

    def _windows(self, frame, shuffle=None):
        windows = make_windows(self.scaler.transform(frame), self.width)
        return shuffle_windows(windows, shuffle) if shuffle is not None else windows

    def _train_windows(self, frames):
        frames = [frames] if isinstance(frames, pd.DataFrame) else list(frames)
        self.scaler = Standardiser(self.columns).fit(_stack(frames))
        return np.concatenate([self._windows(f) for f in frames])


class SeqPCADetector(_WindowDetector):
    def __init__(self, columns, label, width=8, variance_kept=0.90):
        self.columns, self.width, self.variance_kept = columns, width, variance_kept
        self.name = f"Seq-PCA ({label})"

    def fit(self, frames):
        W = self._train_windows(frames).reshape(-1, self.width * len(self.columns))
        self.centre = W.mean(axis=0)
        _, singular_values, components = np.linalg.svd(W - self.centre, full_matrices=False)
        explained = np.cumsum(singular_values ** 2) / np.sum(singular_values ** 2)
        k = int(np.searchsorted(explained, self.variance_kept) + 1)
        self.components = components[:k]
        return self

    def score(self, frame, shuffle=None):
        W = self._windows(frame, shuffle).reshape(-1, self.width * len(self.columns)) - self.centre
        reconstruction = W @ self.components.T @ self.components
        return ((W - reconstruction) ** 2).mean(axis=1)


class LSTMAEDetector(_WindowDetector):
    """LSTM autoencoder (PyTorch). Encoder LSTM -> `latent` numbers -> decoder LSTM -> window."""

    def __init__(self, columns, label, width=8, hidden=32, latent=8, epochs=20,
                 batch_size=256, learning_rate=2e-3, seed=0):
        self.columns, self.width = columns, width
        self.hidden, self.latent, self.epochs = hidden, latent, epochs
        self.batch_size, self.learning_rate, self.seed = batch_size, learning_rate, seed
        self.name = f"LSTM-AE ({label})"

    def fit(self, frames):
        import torch
        torch.manual_seed(self.seed)
        rng = np.random.default_rng(self.seed)
        frames = list(frames)
        # Hold out every tenth training session to decide when training has gone far enough.
        held = [f for i, f in enumerate(frames) if i % 10 == 9] or frames[-1:]
        fit_on = [f for i, f in enumerate(frames) if i % 10 != 9] or frames
        X = self._train_windows(fit_on).astype(np.float32)
        V = np.concatenate([self._windows(f) for f in held]).astype(np.float32)
        self.model = _build_lstm_ae(len(self.columns), self.hidden, self.latent)
        opt = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        best, best_state, self.history = np.inf, None, []
        Xt, Vt = torch.from_numpy(X), torch.from_numpy(V)
        for _ in range(self.epochs):
            self.model.train()
            for batch in np.array_split(rng.permutation(len(X)), max(1, len(X) // self.batch_size)):
                xb = Xt[batch]
                loss = ((self.model(xb) - xb) ** 2).mean()
                opt.zero_grad()
                loss.backward()
                opt.step()
            self.model.eval()
            with torch.no_grad():
                val = float(((self.model(Vt) - Vt) ** 2).mean())
            self.history.append(val)
            if val < best:
                best = val
                best_state = {k: v.clone() for k, v in self.model.state_dict().items()}
        self.model.load_state_dict(best_state)
        self.model.eval()
        return self

    def score(self, frame, shuffle=None):
        import torch
        W = torch.from_numpy(self._windows(frame, shuffle).astype(np.float32))
        with torch.no_grad():
            error = ((self.model(W) - W) ** 2).mean(dim=(1, 2))
        return error.numpy().astype(float)


def _build_lstm_ae(n_features, hidden, latent):
    import torch
    from torch import nn

    class LSTMAutoencoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.LSTM(n_features, hidden, batch_first=True)
            self.to_latent = nn.Linear(hidden, latent)
            self.from_latent = nn.Linear(latent, hidden)
            self.decoder = nn.LSTM(hidden, hidden, batch_first=True)
            self.output = nn.Linear(hidden, n_features)

        def forward(self, x):
            _, (h, _) = self.encoder(x)                    # summary of the whole window
            z = self.to_latent(h[-1])                      # squeezed to `latent` numbers
            start = self.from_latent(z).unsqueeze(1).repeat(1, x.shape[1], 1)
            y, _ = self.decoder(start)                     # unroll back into a sequence
            return self.output(y)

    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    return LSTMAutoencoder()
