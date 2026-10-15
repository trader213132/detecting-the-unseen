from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from run_emergence import ledger, ci


def test_execution_reward_counts_auxiliary_trades_and_round_trip_cost():
    # Buy 3 for the client at 99; an extra sell fills at 98 and must be bought
    # back at 101. The three-tick round-trip loss cancels the client's surplus.
    events = pd.DataFrame([
        dict(kind="TRADE", time=1, agent_id=7, aggressor_id=8, side=1, qty=3, price=99, order_id=1),
        dict(kind="TRADE", time=2, agent_id=7, aggressor_id=8, side=-1, qty=1, price=98, order_id=2),
        dict(kind="TRADE", time=3, agent_id=8, aggressor_id=7, side=-1, qty=1, price=101, order_id=3),
        dict(kind="TRADE", time=3, agent_id=7, aggressor_id=7, side=1, qty=10, price=100, order_id=4),
    ])
    ep = dict(start=0, end=3, account=7, task_side=1, mid0=100, walls=[(2, 98)])
    result = ledger(SimpleNamespace(events=events, seed=1), ep)
    assert result["inventory"] == 3
    assert result["reward"] == 0
    assert result["extra_filled_lots"] == 1
    # A self-match produces no cash or inventory gain, but counts both fee legs.
    assert result["turnover"] == 25


def test_incomplete_client_order_cannot_masquerade_as_profit():
    events = pd.DataFrame([dict(kind="TRADE", time=1, agent_id=7, aggressor_id=8,
                               side=1, qty=2, price=99, order_id=1)])
    with pytest.raises(ValueError, match="Unfilled inventory"):
        ledger(SimpleNamespace(events=events, seed=2),
               dict(start=0, end=2, account=7, task_side=1, mid0=100, walls=[]))


def test_paired_interval_collapses_for_identical_policies():
    assert ci(np.zeros(128)) == [0., 0., 0.]
