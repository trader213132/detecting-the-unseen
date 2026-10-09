"""Turn a session's event log into one row of features per bar.

Two feature sets, which is the heart of the experiment:

GENERIC: a standard description of the order book that any limit-order-book
    machine-learning paper would use (depth at the top price levels, spread,
    price change, counts and volumes of each event type). It is chosen without
    thinking about spoofing at all.

INFORMED: extra features that only make sense if you already know what spoofing
    looks like: the largest single order, large orders cancelled quickly, how
    far behind the best price a big order was placed, book imbalance and signed
    order flow. Using these quietly "teaches" the detector about spoofing.

Every feature for bar b uses only events up to the end of bar b (no peeking ahead).
"""
import numpy as np
import pandas as pd

from . import config as C
from .orderbook import BUY

LEVELS = range(1, 6)
GENERIC = ([f"bid_depth_{k}" for k in LEVELS] + [f"ask_depth_{k}" for k in LEVELS] +
           ["spread", "mid_change", "n_add", "n_cancel", "n_trade",
            "vol_add", "vol_cancel", "vol_trade"])
INFORMED_EXTRA = ["max_add", "max_fast_cancel", "big_add_distance",
                  "imbalance", "imbalance_change", "signed_flow"]
INFORMED = GENERIC + INFORMED_EXTRA

# Heavy-tailed counts and sizes are log-transformed before modelling.
LOG_FEATURES = ([f"bid_depth_{k}" for k in LEVELS] + [f"ask_depth_{k}" for k in LEVELS] +
                ["n_add", "n_cancel", "n_trade", "vol_add", "vol_cancel", "vol_trade",
                 "max_add", "max_fast_cancel"])


def bar_features(session, fast_cancel_steps=C.FAST_CANCEL_STEPS):
    cfg = session.cfg
    n_bars = cfg.steps // cfg.bar_steps
    ev = session.events
    bar = (ev["time"].to_numpy() // cfg.bar_steps).astype(int)
    kind = ev["kind"].to_numpy()
    qty = ev["qty"].to_numpy(dtype=float)
    side = ev["side"].to_numpy()
    is_add, is_cancel, is_trade = kind == "ADD", kind == "CANCEL", kind == "TRADE"

    def count(mask):
        return np.bincount(bar[mask], minlength=n_bars).astype(float)

    def total(mask, values):
        return np.bincount(bar[mask], weights=values[mask], minlength=n_bars)

    def largest(mask, values):
        out = np.zeros(n_bars)
        np.maximum.at(out, bar[mask], values[mask])
        return out

    f = {}
    for k in LEVELS:
        f[f"bid_depth_{k}"] = session.bid_depth[:, k - 1]
        f[f"ask_depth_{k}"] = session.ask_depth[:, k - 1]
    f["spread"] = np.nan_to_num(session.best_ask - session.best_bid, nan=0.0)
    mid = session.mid[cfg.bar_steps - 1::cfg.bar_steps]            # mid at each bar end
    f["mid_change"] = np.diff(mid, prepend=mid[0])
    f["n_add"], f["n_cancel"], f["n_trade"] = count(is_add), count(is_cancel), count(is_trade)
    f["vol_add"] = total(is_add, qty)
    f["vol_cancel"] = total(is_cancel, qty)
    f["vol_trade"] = total(is_trade, qty)

    # --- spoof-informed features --------------------------------------------
    f["max_add"] = largest(is_add, qty)
    lifetime = ev["time"].to_numpy() - ev["order_time"].to_numpy()
    f["max_fast_cancel"] = largest(is_cancel & (lifetime <= fast_cancel_steps), qty)
    f["big_add_distance"] = _distance_of_largest_add(ev, bar, is_add, qty, side, n_bars)
    bids, asks = session.bid_depth.sum(axis=1), session.ask_depth.sum(axis=1)
    imbalance = np.where(bids + asks > 0, (bids - asks) / np.maximum(bids + asks, 1), 0.0)
    f["imbalance"] = imbalance
    f["imbalance_change"] = np.diff(imbalance, prepend=imbalance[0])
    aggressor_sign = -side                                             # the side that crossed
    f["signed_flow"] = total(is_trade, aggressor_sign * qty)

    frame = pd.DataFrame(f)
    frame.insert(0, "bar", np.arange(n_bars))
    return frame


def _distance_of_largest_add(ev, bar, is_add, qty, side, n_bars):
    """Ticks behind the best price of the biggest order added in each bar (0 = at or inside it)."""
    price = ev["price"].to_numpy(dtype=float)
    best_bid = ev["best_bid"].to_numpy(dtype=float)
    best_ask = ev["best_ask"].to_numpy(dtype=float)
    distance = np.where(side == BUY, best_bid - price, price - best_ask)
    distance = np.clip(np.nan_to_num(distance, nan=0.0), 0, 10)

    out = np.zeros(n_bars)
    idx = np.nonzero(is_add)[0]
    if len(idx) == 0:
        return out
    order = idx[np.lexsort((qty[idx], bar[idx]))]          # sort by bar, then by size
    last_in_bar = np.r_[np.nonzero(np.diff(bar[order]))[0], len(order) - 1]
    chosen = order[last_in_bar]                             # biggest add in each bar
    out[bar[chosen]] = distance[chosen]
    return out


def episode_windows(session):
    """For each special episode: the bars a detector must alert in to "catch" it.

    The window runs from the bar the large order appears to the bar after the
    longest a spoof could last, so spoofs and controls get identical windows.
    """
    cfg = session.cfg
    windows = []
    for ep in session.episodes:
        first = ep["start"] // cfg.bar_steps
        last = (ep["start"] + C.MAX_EPISODE_STEPS) // cfg.bar_steps + 1
        windows.append({"kind": ep["kind"], "size_mult": ep["size_mult"],
                        "first_bar": first, "last_bar": last})
    return windows
