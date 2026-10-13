"""Account-level surveillance: what each trader did, window by window.

A regulator receives every order together with the account that placed it. This module
turns a session's event log into one row per (account, window): how many lots the
account added, cancelled and traded on each side. Windows are WINDOW steps long and a
new one starts every STRIDE steps, so any spoof (at most 30 steps) fits inside one.

Two detectors read these rows:

  * PRINCIPLE. UK market abuse law (MAR Article 12) defines this kind of manipulation by
    what it does, not by what it looks like: orders that give a false or misleading signal
    about supply or demand. Turned into three clauses about one account in one window:
      1. it SHOWED interest on one side: it submitted more lots there than on the other;
      2. that interest was WITHDRAWN, not traded: it cancelled more on that side; and
      3. it TRADED THE OTHER WAY: on balance it sold while showing buying interest, or
         bought while showing selling interest.
    The score is the size of the false signal, min(1, 2) in lots, if 3 holds; else zero.
      - Nothing in it mentions size, lifetime, distance or any spoofing example.
      - It needs no training at all; only its alert threshold is set on normal data.
      - "Net" matters: a market maker submits the same quotes on both sides, which says
        nothing about direction, so clause 1 rules it out however much it cancels.

  * UNTAUGHT (ACCOUNTS). An Isolation Forest given exactly the same rows (the nine counts
    in FIELDS, log-scaled) and nothing else. It is the control: if it does as well as the
    principle, the success comes from the account data, not from the principle.

SEEN BY THE MARKET (Part 4). The challenger found two holes in the principle as first written.
A large order far from the best price, on the other side, cancels the wall out of the "net"
sums while no trader can see it; and an honest market maker that quotes more on one side
looks like a spoofer. So the refined version weighs every resting order by how often book-
reading traders can actually see a price that far from the best (`weights`, measured on
normal trading), at the closest the order came to the best price while it was alive, and
leaves out orders placed AT the best price: those are the next to trade, a real offer
rather than a signal. Pass weights to account_rows / lifetime_scores.

pair_score() is the attack test's fallback: the same clauses when the "trading the other
way" may happen in ANY other account, for a spoofer who splits the trick across two.
"""
import numpy as np
import pandas as pd

WINDOW = 40          # steps: the same span as an episode window
STRIDE = 10          # a window starts every 10 steps
START = 300          # episodes never start before this step, so windows start here too
FIELDS = ["added_buy", "added_sell", "cancelled_buy", "cancelled_sell", "traded_buy", "traded_sell",
          "aggressive_buy", "aggressive_sell", "orders"]
A_BUY, A_SELL, C_BUY, C_SELL, T_BUY, T_SELL, G_BUY, G_SELL, N_ORDERS = range(len(FIELDS))
# added_*: lots that rested on the book; aggressive_*: lots that traded the moment they were
# submitted (so never rested); traded_*: all lots traded, resting or aggressive.


def placement_distance(events):
    """Ticks behind its own side's best price at which each event's order was placed
    (0 = at or better than the best price). Cancels and trades inherit their order's value."""
    add = events.kind.to_numpy() == "ADD"
    side, price = events.side.to_numpy(), events.price.to_numpy(dtype=float)
    best = np.where(side == 1, events.best_bid.to_numpy(dtype=float), events.best_ask.to_numpy(dtype=float))
    d = np.clip(np.nan_to_num(side * (best - price), nan=0.0), 0, None)
    ids = events.order_id.to_numpy()
    lookup = dict(zip(ids[add], d[add]))
    return np.array([lookup.get(i, 0.0) for i in ids]) if len(ids) else d


def signal_weights(events, weights):
    """How visible each event's order was as a signal to book-reading traders: weights[d] at the
    CLOSEST distance d (ticks behind its side's best price, at least 1) that the order reached while
    it was alive. An order far away that the price drifts towards becomes visible, so it counts.
    An order placed at or better than the best price weighs 0: it is the next to trade, a real offer.
    Cancels and trades inherit their order's weight."""
    w = np.asarray(weights, float)
    t, kind, ids = events.time.to_numpy(), events.kind.to_numpy(), events.order_id.to_numpy()
    side, price = events.side.to_numpy(), events.price.to_numpy(dtype=float)
    # The best bid and ask at every step (the last value recorded at or before it).
    steps = int(t.max()) + 1 if len(t) else 1
    at = np.searchsorted(t, np.arange(steps), side="right") - 1
    best = {s: pd.Series(np.where(at >= 0, events[col].to_numpy(dtype=float)[np.maximum(at, 0)], np.nan)).ffill().to_numpy()
            for s, col in ((1, "best_bid"), (-1, "best_ask"))}
    last = pd.Series(t).groupby(ids).max()                       # when each order last appears (cancel, final trade)
    placed = placement_distance(events)
    out = {}
    for i in np.nonzero(kind == "ADD")[0]:
        if placed[i] < 1:
            out[ids[i]] = 0.0
            continue
        life = best[side[i]][t[i]:last[ids[i]] + 1]
        d = side[i] * (life - price[i])
        closest = int(max(1, np.nanmin(d))) if np.isfinite(d).any() else int(placed[i])
        out[ids[i]] = w[closest] if closest < len(w) else 0.0
    return np.array([out.get(i, 0.0) for i in ids])


def _activity(events, weights=None):
    """(time, account, field, lots) for every event, from each account's point of view.
    weights (optional): weights[d] multiplies the lots of resting orders placed d ticks behind
    the best price, in the added and cancelled counts (orders beyond the list count 0)."""
    t, kind, acc, side, qty, agg = (events[c].to_numpy() for c in
                                    ["time", "kind", "agent_id", "side", "qty", "aggressor_id"])
    buy = side == 1
    parts = []
    add, can, trd = kind == "ADD", kind == "CANCEL", kind == "TRADE"
    shown = qty.astype(float)
    if weights is not None:
        shown = shown * signal_weights(events, weights)
    parts.append((t[add], acc[add], np.where(buy[add], A_BUY, A_SELL), shown[add]))
    parts.append((t[add], acc[add], np.full(add.sum(), N_ORDERS), np.ones(add.sum())))
    parts.append((t[can], acc[can], np.where(buy[can], C_BUY, C_SELL), shown[can]))
    # A trade involves two accounts: the resting order's owner trades on its side,
    # the aggressor on the opposite side.
    parts.append((t[trd], acc[trd], np.where(buy[trd], T_BUY, T_SELL), qty[trd]))
    parts.append((t[trd], agg[trd], np.where(buy[trd], T_SELL, T_BUY), qty[trd]))
    parts.append((t[trd], agg[trd], np.where(buy[trd], G_SELL, G_BUY), qty[trd]))
    return [np.concatenate(x) for x in zip(*parts)]


def account_rows(session, window=WINDOW, stride=STRIDE, start=START, owners=None, weights=None):
    """One row per (window, active account). `owners` optionally maps account numbers to the
    person who owns them (as a regulator could), so that one person's accounts count as one.

    Returns a dict: starts (window start times), win (window index of each row),
    account (account number of each row), X (one row of lot counts each, as in FIELDS)."""
    t, acc, field, lots = _activity(session.events, weights)
    for account, owner in (owners or {}).items():
        acc = np.where(acc == account, owner, acc)
    steps = session.cfg.steps
    n_bins = steps // stride
    accounts, a_idx = np.unique(acc, return_inverse=True)
    grid = np.zeros((n_bins + 1, len(accounts), len(FIELDS)), np.float32)
    np.add.at(grid, (t // stride + 1, a_idx, field), lots)
    cum = np.cumsum(grid, axis=0)                               # cum[b] = everything before bin b
    per = window // stride
    first = start // stride
    starts = np.arange(first, n_bins - per + 1)                 # window = bins b .. b+per-1
    sums = cum[starts + per] - cum[starts]                      # (n_windows, n_accounts, fields)
    active = sums.any(axis=2)
    w_idx, a_sel = np.nonzero(active)
    return {"starts": starts * stride, "win": w_idx.astype(np.int32), "account": accounts[a_sel].astype(np.int32),
            "X": sums[w_idx, a_sel].astype(np.float32)}


def principle_score(X):
    """Size (lots) of a one-sided signal that was withdrawn while the account traded the other way."""
    shown = (X[:, A_BUY] + X[:, G_BUY]) - (X[:, A_SELL] + X[:, G_SELL])   # > 0: showed interest to BUY
    withdrawn = X[:, C_BUY] - X[:, C_SELL]                                 # > 0: withdrew more buying interest
    sold = X[:, T_SELL] - X[:, T_BUY]                                      # > 0: sold more than it bought
    buy_signal = (shown > 0) & (withdrawn > 0) & (sold > 0)
    sell_signal = (shown < 0) & (withdrawn < 0) & (sold < 0)
    size = np.minimum(np.abs(shown), np.abs(withdrawn))
    return np.where(buy_signal | sell_signal, size, 0.0)


def generic_features(X):
    """What the untaught detector sees: the same counts, log-scaled."""
    return np.log1p(X)


def window_max(rows, scores):
    """The highest score of any account in each window (0 if no account was active)."""
    out = np.zeros(len(rows["starts"]))
    np.maximum.at(out, rows["win"], scores)
    return out


def episode_score(rows, scores, start, account, span=WINDOW):
    """The episode account's highest score in any window that overlaps the episode."""
    s = rows["starts"][rows["win"]]
    mask = (rows["account"] == account) & (s > start - span) & (s < start + span)
    return float(scores[mask].max()) if mask.any() else 0.0


def span_maxes(rows, scores, span=WINDOW, stride=STRIDE):
    """For NORMAL sessions: the highest score of any account over each stretch an episode
    window could cover (all windows overlapping a span-long stretch). The comparison set
    for 'is the spoofer more suspicious than the most suspicious honest trader nearby?'."""
    w = window_max(rows, scores)
    k = 2 * span // stride - 1                       # windows overlapping one episode
    if len(w) < k:
        return np.array([])
    return np.lib.stride_tricks.sliding_window_view(w, k).max(axis=1)[::span // stride]


def lifetime_scores(session, weights=None):
    """The principle without any fixed window. For every withdrawn (cancelled) order, the three
    clauses are measured for its owner over that order's own life, from the step it was placed
    to the step it was withdrawn. A spoofer who waits before pulling the wall cannot escape:
    the wall was alive while the genuine order traded, however long the wait.

    Returns (cancel times, accounts, scores), one entry per cancellation."""
    t, acc, field, lots = _activity(session.events, weights)
    ev = session.events
    can = ev[ev.kind == "CANCEL"]
    c_time, c_acc, c_placed = can.time.to_numpy(), can.agent_id.to_numpy(), can.order_time.to_numpy()
    scores = np.zeros(len(can))
    order = np.lexsort((t, acc))
    t, acc, field, lots = t[order], acc[order], field[order], lots[order]
    bounds = np.searchsorted(acc, np.unique(acc))
    for a_id, lo in zip(np.unique(acc), bounds):
        hi = np.searchsorted(acc, a_id, side="right")
        mine = np.nonzero(c_acc == a_id)[0]
        if len(mine) == 0:
            continue
        times = t[lo:hi]
        steps = np.zeros((hi - lo + 1, len(FIELDS)))
        steps[np.arange(1, hi - lo + 1), field[lo:hi]] = lots[lo:hi]
        cum = np.cumsum(steps, axis=0)                           # cum[k] = this account's first k events
        first = np.searchsorted(times, c_placed[mine], side="left")
        last = np.searchsorted(times, c_time[mine], side="right")
        scores[mine] = principle_score(cum[last] - cum[first])
    return c_time, c_acc, scores


def lifetime_window_max(session, c_time, scores, window=WINDOW, start=START):
    """Highest order-life score among cancellations in each window (for the alert threshold)."""
    n = (session.cfg.steps - start) // window
    out = np.zeros(n)
    k = (c_time - start) // window
    ok = (k >= 0) & (k < n)
    np.maximum.at(out, k[ok], scores[ok])
    return out


def pair_score(rows, X):
    """Without knowing who owns which account: an account's one-sided signal that it withdrew,
    counted if ANY OTHER account in the same window traded the other way on balance. It is
    the only way to look for a spoofer who splits the trick across two unlinked accounts."""
    shown = (X[:, A_BUY] + X[:, G_BUY]) - (X[:, A_SELL] + X[:, G_SELL])
    withdrawn = X[:, C_BUY] - X[:, C_SELL]
    sold = X[:, T_SELL] - X[:, T_BUY]
    n = len(rows["starts"])
    sellers = np.bincount(rows["win"], weights=sold > 0, minlength=n)[rows["win"]] - (sold > 0)
    buyers = np.bincount(rows["win"], weights=sold < 0, minlength=n)[rows["win"]] - (sold < 0)
    size = np.minimum(np.abs(shown), np.abs(withdrawn))
    buy_signal = (shown > 0) & (withdrawn > 0) & (sellers > 0)
    sell_signal = (shown < 0) & (withdrawn < 0) & (buyers > 0)
    return np.where(buy_signal | sell_signal, size, 0.0)
