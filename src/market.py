"""Agent-based simulation of one trading session.

The NORMAL market is made of four kinds of trader:
  * ZI ("zero intelligence") traders: they ignore the order book and trade
    around a noisy estimate of the asset's fundamental value.
  * Reactive traders: they read the order book. Heavy bids make them think the
    price will rise, so they value the asset more and lean towards buying. This
    is a simplified version of the book-reading "HBL" traders of Wang &
    Wellman (2017), and it is exactly the behaviour spoofing exploits.
  * Market makers: they quote both sides and cancel/replace every few steps, so
    lots of fast cancellations are perfectly normal.
  * An institution: once in a while it rests a genuinely large order a tick or
    two behind the best price and leaves it there.

TEST sessions can also contain scheduled "special" episodes:
  * "spoof":   the Tribunal pattern. A large order (the "wall") is placed one or
               two ticks behind the best price. A small genuine order goes on the
               OTHER side at the best price. When the small order fills, or after
               MAX_EPISODE_STEPS, the wall is cancelled.
  * "layer":   layering. The same total wall size is split into LAYERS smaller
               orders on successive price levels. It is a variant the rule-based
               detector was NOT written for.
  * "honest":  the same small genuine order with no wall. Running a session with
               the same seed in both modes measures what the wall itself did.
  * "control": a legitimate large order of the same size and placement as a spoof
               wall, which stays on the book for a long time.
"""
import heapq
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from . import config as C
from .orderbook import BUY, LOG_COLUMNS, SELL, OrderBook

# Agent ids are only used to label episodes afterwards. Detectors never see them.
ZI, REACTIVE, MARKET_MAKER, INSTITUTION, SPOOFER, CONTROL = range(6)


def agent_id(kind, index=0):
    return kind * 1000 + index


@dataclass
class Session:
    events: pd.DataFrame        # the market-by-order event log
    bid_depth: np.ndarray       # (n_bars, depth_levels) quantity at the best bid levels at each bar end
    ask_depth: np.ndarray
    best_bid: np.ndarray        # (n_bars,)
    best_ask: np.ndarray
    mid: np.ndarray             # (steps,) mid price after every step
    fundamental: np.ndarray     # (steps,)
    episodes: list              # dicts describing each special episode
    regime: str
    seed: int
    cfg: C.MarketConfig         # the exact market settings used


def plan_episodes(seed, n, steps):
    """Choose when special episodes happen. Uses its own random generator, so a
    spoof session and its honest twin get exactly the same schedule."""
    rng = np.random.default_rng([seed, 99])
    starts = []
    while len(starts) < n:
        start = int(rng.integers(300, steps - 150))
        if all(abs(start - other) >= 250 for other in starts):
            starts.append(start)
    plans = []
    for start in sorted(starts):
        plans.append({
            "start": start,
            "wall_side": int(rng.choice([BUY, SELL])),
            "distance": int(rng.integers(1, 3)),    # 1 or 2 ticks behind the touch
            "control_life": int(rng.integers(*C.CONTROL_LIFE)),
        })
    return plans


def run_session(seed, regime="calm", specials=(), overrides=None):
    """Simulate one session.

    specials:  list of (kind, size_multiplier) tuples, e.g. [("spoof", 8), ("spoof", 8)].
    overrides: optional dict of MarketConfig fields to change (used by the sensitivity analysis).
    """
    cfg = replace(C.REGIMES[regime], **(overrides or {}))
    rng = np.random.default_rng(seed)
    book = OrderBook()
    expiries = []                                  # heap of (cancel_time, order_id)
    mm_orders = [[] for _ in range(cfg.n_market_makers)]

    plans = plan_episodes(seed, len(specials), cfg.steps)
    queued = [dict(plan, kind=kind, size_mult=size) for plan, (kind, size) in zip(plans, specials)]
    active = []
    finished = []

    n_bars = cfg.steps // cfg.bar_steps
    bid_depth = np.zeros((n_bars, cfg.depth_levels))
    ask_depth = np.zeros((n_bars, cfg.depth_levels))
    best_bid = np.zeros(n_bars)
    best_ask = np.zeros(n_bars)
    mids = np.zeros(cfg.steps)
    fundamentals = np.zeros(cfg.steps)

    value = cfg.fundamental_mean
    last_mid = value
    for t in range(cfg.steps):
        # 1. The fundamental value drifts (and sometimes jumps on "news").
        value += cfg.mean_reversion * (cfg.fundamental_mean - value)
        value += cfg.fundamental_vol * rng.standard_normal()
        jump = rng.standard_normal()
        if rng.random() < cfg.jump_prob:
            value += cfg.jump_size * jump

        # 2. Impatient traders cancel orders that have waited too long.
        while expiries and expiries[0][0] <= t:
            _, order_id = heapq.heappop(expiries)
            book.cancel(order_id, t)

        # 3. Market makers cancel and replace their quotes.
        for i in range(cfg.n_market_makers):
            if (t + 2 * i) % cfg.mm_period == 0:
                _requote(book, cfg, rng, value, t, i, mm_orders)

        # 4. Background traders arrive.
        for _ in range(rng.poisson(cfg.arrival_rate)):
            _background_trader(book, cfg, rng, value, t, expiries)

        # 5. Now and then the institution rests a genuinely large order.
        institution_draws = rng.random(5)
        if institution_draws[0] < cfg.institution_rate:
            side = BUY if institution_draws[1] < 0.5 else SELL
            size = round(C.TYPICAL_SIZE * 2 ** (1 + 3 * institution_draws[2]))   # 2x to 16x typical
            distance = 1 + int(institution_draws[3] * 2)
            touch = book.best(side)
            if touch is not None:
                order_id = book.submit(agent_id(INSTITUTION), side, touch - side * distance, size, t)
                if order_id is not None:
                    low, high = cfg.institution_life
                    heapq.heappush(expiries, (t + low + int(institution_draws[4] * (high - low)), order_id))

        # 6. Special episodes (test sessions only).
        while queued and queued[0]["start"] == t:
            episode = queued.pop(0)
            if _start_episode(book, episode, value, t):
                active.append(episode)
        for episode in list(active):
            if _update_episode(book, episode, t):
                active.remove(episode)
                finished.append(episode)

        # 7. Record what the book looks like.
        mid = book.mid()
        last_mid = mid if mid is not None else last_mid
        mids[t] = last_mid
        fundamentals[t] = value
        if (t + 1) % cfg.bar_steps == 0:
            bar = t // cfg.bar_steps
            bid_depth[bar] = book.depth(BUY, cfg.depth_levels)
            ask_depth[bar] = book.depth(SELL, cfg.depth_levels)
            best_bid[bar] = book.best_bid() if book.best_bid() is not None else np.nan
            best_ask[bar] = book.best_ask() if book.best_ask() is not None else np.nan

    events = pd.DataFrame(book.log, columns=LOG_COLUMNS)
    return Session(events, bid_depth, ask_depth, best_bid, best_ask, mids,
                   fundamentals, finished + active, regime, seed, cfg)


def _requote(book, cfg, rng, value, t, i, mm_orders):
    for order_id in mm_orders[i]:
        book.cancel(order_id, t)
    # Market makers also lean their quotes towards the heavier side of the book.
    estimate = value + rng.normal(0, 1.0) + cfg.mm_react_shift * book.imbalance(cfg.depth_levels)
    mm_orders[i] = []
    for level in range(cfg.mm_levels):
        offset = cfg.mm_half_spread + level
        for side in (BUY, SELL):
            price = round(estimate - side * offset)
            order_id = book.submit(agent_id(MARKET_MAKER, i), side, price, cfg.mm_size, t)
            if order_id is not None:
                mm_orders[i].append(order_id)


def _background_trader(book, cfg, rng, value, t, expiries):
    # Every trader makes the same random draws, which keeps paired runs aligned.
    is_reactive, side_draw, surplus_draw, patience = rng.random(4)
    size = int(rng.geometric(cfg.size_p))
    estimate = value + cfg.obs_noise * rng.standard_normal()
    p_buy = 0.5
    if is_reactive < cfg.reactive_share:
        kind = REACTIVE
        imbalance = book.imbalance(cfg.depth_levels)
        estimate += cfg.react_shift * imbalance
        p_buy += cfg.react_bias * imbalance
    else:
        kind = ZI
    side = BUY if side_draw < p_buy else SELL
    surplus = cfg.surplus_min + surplus_draw * (cfg.surplus_max - cfg.surplus_min)
    price = round(estimate - side * surplus)
    order_id = book.submit(agent_id(kind), side, price, size, t)
    if order_id is not None:
        wait = -cfg.mean_patience * np.log(1 - patience)          # exponential waiting time
        heapq.heappush(expiries, (t + max(1, int(wait)), order_id))


def _start_episode(book, ep, value, t):
    wall_side = ep["wall_side"]
    genuine_side = -wall_side
    touch = book.best(wall_side)
    opposite_touch = book.best(genuine_side)
    if touch is None or opposite_touch is None:
        return False
    ep.update(start=t, end=None, walls=[], small_id=None, small_filled=False, fill_time=None)
    total = round(ep["size_mult"] * C.TYPICAL_SIZE)
    if ep["kind"] in ("spoof", "control"):
        # One big order, one or two ticks behind the best price.
        orders = [(touch - wall_side * ep["distance"], total)]
    elif ep["kind"] == "layer":
        # Layering: the same total size split over several price levels.
        piece = max(1, round(total / C.LAYERS))
        orders = [(touch - wall_side * (ep["distance"] + k), piece) for k in range(C.LAYERS)]
    else:
        orders = []
    owner = CONTROL if ep["kind"] == "control" else SPOOFER
    for price, size in orders:
        order_id = book.submit(agent_id(owner), wall_side, price, size, t)
        if order_id is not None:
            ep["walls"].append((order_id, price))
    if ep["kind"] in ("spoof", "layer", "honest"):
        ep["small_id"] = book.submit(agent_id(SPOOFER), genuine_side, opposite_touch,
                                     C.TYPICAL_SIZE, t)
        if ep["small_id"] is None:          # traded immediately
            ep["small_filled"], ep["fill_time"] = True, t
    return True


def _update_episode(book, ep, t):
    """Advance an active episode by one step. Returns True when it has finished."""
    if ep["kind"] == "control":
        still_resting = any(order_id in book.orders for order_id, _ in ep["walls"])
        if t - ep["start"] >= ep["control_life"] or not still_resting:
            for order_id, _ in ep["walls"]:
                book.cancel(order_id, t)
            ep["end"] = t
            return True
        return False

    if not ep["small_filled"] and ep["small_id"] not in book.orders:
        ep["small_filled"], ep["fill_time"] = True, t

    # Pull any wall order early if the price has moved onto it, so it would actually trade.
    for order_id, price in ep["walls"]:
        if order_id in book.orders:
            touch = book.best(ep["wall_side"])
            if (touch - price) * ep["wall_side"] <= 0:
                book.cancel(order_id, t)

    done = ep["small_filled"] or t - ep["start"] >= C.MAX_EPISODE_STEPS
    if done:
        for order_id, _ in ep["walls"]:
            book.cancel(order_id, t)
        if ep["small_id"] is not None:
            book.cancel(ep["small_id"], t)
        ep["end"] = t
    return done
