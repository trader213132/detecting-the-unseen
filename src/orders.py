"""Order-level analysis: describe every individual order instead of slices of the market.

Each order that rests on the book gets four generic numbers, the same for every order:
  size        lots it rested with (log)
  lifetime    steps until it left the book (log), whether by trading or cancelling
  filled      fraction of it that traded
  distance    ticks behind the best price when it was placed (negative = inside the spread)

Nothing here mentions spoofing. Lifetime and the filled fraction are only known once
an order has gone, so this is after-the-fact surveillance (how much real surveillance
works), not a live alarm.
"""
import numpy as np
import pandas as pd

from .orderbook import BUY

ORDER_FEATURES = ["log_size", "log_lifetime", "filled", "distance"]


def order_table(session):
    ev = session.events
    adds = ev[ev.kind == "ADD"].set_index("order_id")
    ends = ev[ev.kind.isin(["CANCEL", "TRADE"])].groupby("order_id").time.max()
    traded = ev[ev.kind == "TRADE"].groupby("order_id").qty.sum()
    cancelled = set(ev[ev.kind == "CANCEL"].order_id)
    t = pd.DataFrame(index=adds.index)
    t["start"] = adds.time
    t["size"] = adds.qty.astype(float)
    t["agent_id"] = adds.agent_id
    still_open = ~t.index.isin(ends.index)
    end = ends.reindex(t.index).fillna(session.cfg.steps - 1)
    t["lifetime"] = (end - t.start).clip(lower=1)
    t["filled"] = (traded.reindex(t.index).fillna(0) / t["size"]).clip(0, 1)
    touch = np.where(adds.side == BUY, adds.best_bid - adds.price, adds.price - adds.best_ask)
    t["distance"] = np.clip(np.nan_to_num(touch, nan=0.0), -5, 10)
    t["cancelled"] = t.index.isin(cancelled)
    t["open_at_end"] = still_open
    t["log_size"] = np.log1p(t["size"])
    t["log_lifetime"] = np.log1p(t["lifetime"])
    return t


def mark_special_orders(table, session):
    """Label (for evaluation only) which orders were spoof walls, layered pieces or genuine large orders."""
    role = pd.Series("background", index=table.index)
    for ep in session.episodes:
        for order_id, _ in ep.get("walls", []):
            if order_id in role.index:
                role[order_id] = {"spoof": "spoof wall", "layer": "layered piece", "control": "genuine large",
                                  "reversal": "honest reversal", "withdrawal": "honest withdrawal"}[ep["kind"]]
    table = table.copy()
    table["role"] = role
    return table
