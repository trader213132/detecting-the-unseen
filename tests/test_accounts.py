import numpy as np

from src import accounts as A
from src.features import bar_features
from src.market import run_session
from src.orderbook import BUY, SELL
from tests.test_features import tiny_session


def row(**lots):
    """One account-window row from named lot counts, e.g. row(added_buy=48, cancelled_buy=48)."""
    x = np.zeros((1, len(A.FIELDS)))
    for name, value in lots.items():
        x[0, A.FIELDS.index(name)] = value
    return x


def test_principle_scores_the_definition_and_nothing_else():
    score = lambda **lots: A.principle_score(row(**lots))[0]
    # A spoofer: shows 48 to buy, withdraws it, and sells 3.
    assert score(added_buy=48, added_sell=3, cancelled_buy=48, traded_sell=3) == 45
    # The same lots split into four orders (layering) are the same signal.
    assert score(added_buy=48, added_sell=3, cancelled_buy=48, traded_sell=3, orders=5) == 45
    # A genuine large order: shown and withdrawn, but the account never traded the other way.
    assert score(added_buy=48, cancelled_buy=48) == 0
    # ... or it traded the SAME way (it bought), which is not a contradiction.
    assert score(added_buy=48, cancelled_buy=40, traded_buy=8) == 0
    # A market maker: equal quotes on both sides say nothing about direction, however much it
    # cancels or which side happened to trade.
    assert score(added_buy=39, aggressive_buy=33, added_sell=72, cancelled_buy=24, cancelled_sell=72, traded_buy=53) == 0
    # Selling interest shown and withdrawn while buying: the mirror image.
    assert score(added_sell=30, added_buy=3, cancelled_sell=30, traded_buy=3) == 27


def test_windows_add_up_each_accounts_activity():
    rows = [
        # time kind     id agent side  price qty order_time aggr bb   ba
        (400, "ADD",    1, 7, BUY,  97,  40, 400, -1, 99, 101),
        (401, "ADD",    2, 7, SELL, 101, 3,  401, -1, 99, 101),
        (405, "TRADE",  2, 7, SELL, 101, 3,  401, 9,  99, 101),   # account 9 bought from account 7
        (405, "CANCEL", 1, 7, BUY,  97,  40, 400, -1, 99, 101),
    ]
    r = A.account_rows(tiny_session(rows))
    w = int(np.where(r["starts"] == 380)[0][0])                   # the window 380-419 holds everything
    get = lambda account: r["X"][(r["win"] == w) & (r["account"] == account)][0]
    seven, nine = get(7), get(9)
    assert seven[A.A_BUY] == 40 and seven[A.C_BUY] == 40 and seven[A.T_SELL] == 3 and seven[A.N_ORDERS] == 2
    assert nine[A.T_BUY] == 3 and nine[A.G_BUY] == 3 and nine[A.N_ORDERS] == 0
    assert A.principle_score(r["X"][(r["win"] == w) & (r["account"] == 7)])[0] == 37


def test_account_numbers_never_change_the_market():
    a = run_session(21, "calm", [("spoof", 8)], {"accounts_per_kind": 10})
    b = run_session(21, "calm", [("spoof", 8)], {"accounts_per_kind": 800, "omnibus_share": 0.2})
    assert np.array_equal(a.mid, b.mid)
    assert np.allclose(bar_features(a).to_numpy(), bar_features(b).to_numpy(), equal_nan=True)
    assert a.events.agent_id.nunique() < b.events.agent_id.nunique()


def test_spoofs_score_their_signal_and_genuine_orders_score_nothing():
    for kind, expect_positive in [("spoof", True), ("layer", True), ("control", False), ("reversal", True)]:
        s = run_session(503, "calm", [(kind, 16)])
        r = A.account_rows(s)
        ep = s.episodes[0]
        value = A.episode_score(r, A.principle_score(r["X"]), ep["start"], ep["account"])
        assert (value > 0) == expect_positive, kind


def test_weighted_logistic_regression_finds_the_separating_feature():
    from run_teaching import logistic_fit
    rng = np.random.default_rng(0)
    normal = rng.normal(0, 1, (2000, 2))
    spoofs = rng.normal(0, 1, (5, 2)) + [4, 0]          # only feature 0 tells them apart
    w = logistic_fit(spoofs, normal, normal[:0])
    assert w[0] > 1 and abs(w[1]) < 0.5 * w[0]


def test_two_account_spoofer_is_invisible_alone_and_visible_when_linked():
    s = run_session(600, "calm", [("spoof", 16)], {"spoofer_accounts": 2})
    ep = s.episodes[0]
    assert ep["accounts"] == [4000, 4001] and ep["small_filled"]
    alone = A.account_rows(s)
    linked = A.account_rows(s, owners={4001: 4000})
    assert A.episode_score(alone, A.principle_score(alone["X"]), ep["start"], ep["account"]) == 0
    assert A.episode_score(linked, A.principle_score(linked["X"]), ep["start"], ep["account"]) > 0
    assert A.episode_score(alone, A.pair_score(alone, alone["X"]), ep["start"], ep["account"]) > 0
