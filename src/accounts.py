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

pair_score() is the attack test's fallback: the same clauses when the "trading the other
way" may happen in ANY other account, for a spoofer who splits the trick across two.
"""
import numpy as np

WINDOW = 40          # steps: the same span as an episode window
STRIDE = 10          # a window starts every 10 steps
START = 300          # episodes never start before this step, so windows start here too
FIELDS = ["added_buy", "added_sell", "cancelled_buy", "cancelled_sell", "traded_buy", "traded_sell",
          "aggressive_buy", "aggressive_sell", "orders"]
A_BUY, A_SELL, C_BUY, C_SELL, T_BUY, T_SELL, G_BUY, G_SELL, N_ORDERS = range(len(FIELDS))
# added_*: lots that rested on the book; aggressive_*: lots that traded the moment they were
# submitted (so never rested); traded_*: all lots traded, resting or aggressive.


def _activity(events):
    """(time, account, field, lots) for every event, from each account's point of view."""
    t, kind, acc, side, qty, agg = (events[c].to_numpy() for c in
                                    ["time", "kind", "agent_id", "side", "qty", "aggressor_id"])
    buy = side == 1
    parts = []
    add, can, trd = kind == "ADD", kind == "CANCEL", kind == "TRADE"
    parts.append((t[add], acc[add], np.where(buy[add], A_BUY, A_SELL), qty[add]))
    parts.append((t[add], acc[add], np.full(add.sum(), N_ORDERS), np.ones(add.sum(), int)))
    parts.append((t[can], acc[can], np.where(buy[can], C_BUY, C_SELL), qty[can]))
    # A trade involves two accounts: the resting order's owner trades on its side,
    # the aggressor on the opposite side.
    parts.append((t[trd], acc[trd], np.where(buy[trd], T_BUY, T_SELL), qty[trd]))
    parts.append((t[trd], agg[trd], np.where(buy[trd], T_SELL, T_BUY), qty[trd]))
    parts.append((t[trd], agg[trd], np.where(buy[trd], G_SELL, G_BUY), qty[trd]))
    return [np.concatenate(x) for x in zip(*parts)]


def account_rows(session, window=WINDOW, stride=STRIDE, start=START, owners=None):
    """One row per (window, active account). `owners` optionally maps account numbers to the
    person who owns them (as a regulator could), so that one person's accounts count as one.

    Returns a dict: starts (window start times), win (window index of each row),
    account (account number of each row), X (one row of lot counts each, as in FIELDS)."""
    t, acc, field, lots = _activity(session.events)
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
