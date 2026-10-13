"""Part 4: the challenger's controls in the simulator, and the 'as the market sees it' detector."""
import numpy as np
import pandas as pd

from src import accounts as A
from src.market import CONTROL, SPOOFER, agent_id, run_session
from src.orderbook import BUY, LOG_COLUMNS, SELL

SEEN = np.array([0, 1, 1, 1, 1, 0.15, 0.03, 0.01, 0.01])      # visibility weights, as measured on normal trading


def episode_score(session, ep, weights=None):
    c_time, c_acc, sc = A.lifetime_scores(session, weights)
    mine = (c_acc == ep["account"]) & (c_time >= ep["start"]) & (c_time <= ep["end"])
    return sc[mine].max() if mine.any() else 0.0


def test_new_settings_are_off_by_default():
    a = run_session(10_016, "calm", [("spoof", 16)] * 2)
    b = run_session(10_016, "calm", [("spoof", 16)] * 2, {"spoof_distance": -1, "spoof_layers": 0, "decoy_frac": 0.0})
    pd.testing.assert_frame_equal(a.events, b.events)


def test_the_fair_twin_has_no_wall_and_nothing_else_changes_before_it():
    s = run_session(10_016, "calm", [("spoof", 16)] * 2, {"decoy_frac": 0.5})
    twin = run_session(10_016, "calm", [("spoof", 16)] * 2, {"decoy_frac": 0.5, "spoof_wall": False})
    assert all(ep["walls"] for ep in s.episodes) and not any(ep["walls"] for ep in twin.episodes)
    assert all(ep["decoys"] for ep in twin.episodes)                  # the decoy is still there
    first = s.episodes[0]["start"]
    pd.testing.assert_frame_equal(s.events[s.events.time < first], twin.events[twin.events.time < first])


def test_a_far_decoy_blinds_the_net_principle_but_not_the_seen_version():
    s = run_session(10_016, "calm", [("spoof", 16)] * 2, {"decoy_frac": 1.0, "decoy_distance": 8})
    for ep in s.episodes:
        assert ep["account"] == agent_id(SPOOFER)
        assert episode_score(s, ep) == 0                              # the decoy cancels the wall out
        assert episode_score(s, ep, SEEN) > 30                        # nobody can see the decoy


def test_orders_placed_at_the_best_price_carry_no_signal():
    rows = [
        # time kind   id agent side price qty order_time aggr bb   ba
        (400, "ADD",   1, 7, BUY,  99,  40, 400, -1, 99, 101),     # joins the best bid: a real offer
        (400, "ADD",   2, 7, BUY,  97,  40, 400, -1, 99, 101),     # two ticks back: a signal
        (401, "ADD",   3, 7, BUY,  90,  40, 401, -1, 99, 101),     # nine ticks back: invisible
        (410, "CANCEL", 1, 7, BUY, 99,  40, 400, -1, 99, 101),
        (410, "CANCEL", 2, 7, BUY, 97,  40, 400, -1, 99, 101),
        (410, "CANCEL", 3, 7, BUY, 90,  40, 401, -1, 99, 101),
    ]
    w = A.signal_weights(pd.DataFrame(rows, columns=LOG_COLUMNS), SEEN)
    assert list(w) == [0, 1, 0, 0, 1, 0]


def test_a_far_order_the_price_drifts_towards_becomes_visible():
    rows = [
        (400, "ADD",    1, 7, BUY, 94, 40, 400, -1, 100, 102),     # six ticks back when placed
        (420, "ADD",    2, 8, SELL, 97, 1, 420, -1, 96, 98),        # by now the best bid is 96: two ticks away
        (430, "CANCEL", 1, 7, BUY, 94, 40, 400, -1, 96, 98),
    ]
    w = A.signal_weights(pd.DataFrame(rows, columns=LOG_COLUMNS), SEEN)
    assert w[0] == 1 and w[2] == 1


def test_the_skewing_market_maker_quotes_more_on_the_side_that_closes_its_position():
    s = run_session(65_016, "calm", [("skew", 16)] * 2)
    ev = s.events[(s.events.agent_id == agent_id(CONTROL)) & (s.events.kind == "ADD")]
    for ep in s.episodes:
        mine = ev[(ev.time >= ep["start"]) & (ev.time < ep["start"] + 5)]
        heavy = mine[mine.side == ep["wall_side"]].qty.sum()
        light = mine[mine.side == -ep["wall_side"]].qty.sum()
        assert heavy > light                                           # it starts with a position to close
        assert ep["end"] - ep["start"] >= 150
