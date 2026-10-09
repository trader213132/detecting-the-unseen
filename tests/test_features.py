import numpy as np
import pandas as pd

from src import config as C
from src.features import GENERIC, INFORMED, bar_features
from src.market import Session, run_session
from src.orderbook import BUY, LOG_COLUMNS, SELL


def tiny_session(rows):
    """A hand-made session: 2000 steps, empty book snapshots, the given events."""
    cfg = C.REGIMES["calm"]
    n_bars = cfg.steps // cfg.bar_steps
    zeros = np.zeros((n_bars, cfg.depth_levels))
    return Session(pd.DataFrame(rows, columns=LOG_COLUMNS), zeros, zeros,
                   np.full(n_bars, 99.0), np.full(n_bars, 101.0),
                   np.full(cfg.steps, 100.0), np.full(cfg.steps, 100.0), [], "calm", 0, cfg)


def test_counts_volumes_and_fast_cancel():
    rows = [
        # time kind     id agent side  price qty order_time aggr bb   ba
        (0, "ADD",     1, 5, BUY,  97,  40, 0,  -1, 99, 101),   # big order, 2 ticks behind
        (1, "ADD",     2, 5, SELL, 101, 3,  1,  -1, 99, 101),
        (3, "CANCEL",  1, 5, BUY,  97,  40, 0,  -1, 99, 101),   # cancelled after 3 steps
        (7, "TRADE",   2, 5, SELL, 101, 3,  1,  9,  99, 101),   # buyer lifted the ask
        (8, "CANCEL",  3, 6, BUY,  98,  9,  -100, -1, 99, 101), # slow cancel (lived 108 steps)
    ]
    f = bar_features(tiny_session(rows))
    first, second = f.iloc[0], f.iloc[1]
    assert first["n_add"] == 2 and first["vol_add"] == 43
    assert first["max_add"] == 40 and first["big_add_distance"] == 2
    assert first["max_fast_cancel"] == 40
    assert second["n_trade"] == 1 and second["signed_flow"] == 3
    assert second["vol_cancel"] == 9 and second["max_fast_cancel"] == 0


def test_real_session_has_all_columns_and_no_gaps():
    f = bar_features(run_session(5, "calm"))
    assert set(INFORMED) <= set(f.columns) and set(GENERIC) <= set(INFORMED)
    assert len(f) == C.REGIMES["calm"].steps // C.REGIMES["calm"].bar_steps
    assert not f[INFORMED].isna().any().any()


def test_spoof_and_honest_twins_share_a_schedule_and_history():
    spoof = run_session(11, "calm", [("spoof", 8)])
    honest = run_session(11, "calm", [("honest", 8)])
    start = spoof.episodes[0]["start"]
    assert start == honest.episodes[0]["start"]
    assert np.array_equal(spoof.mid[:start], honest.mid[:start])
