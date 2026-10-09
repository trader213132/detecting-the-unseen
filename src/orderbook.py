"""A minimal limit-order book with price-time priority.

How it works:
  * Buy orders (bids) and sell orders (asks) rest on the book at a price.
  * A new order that crosses the opposite side trades straight away, against the
    best price first and, within a price, the oldest order first.
  * Any quantity left over rests on the book until it is filled or cancelled.

Every change is written to `self.log`, like a real market-by-order data feed:
    (time, kind, order_id, agent_id, side, price, qty, order_time,
     aggressor_id, best_bid, best_ask)
  kind is "ADD", "CANCEL" or "TRADE". For a TRADE the order fields describe the
  resting order that was hit. best_bid/best_ask are the prices just BEFORE the event.
  agent_id is kept only so experiments can label episodes afterwards; detectors
  never see it.
"""
from collections import deque

BUY = 1
SELL = -1

LOG_COLUMNS = ["time", "kind", "order_id", "agent_id", "side", "price", "qty",
               "order_time", "aggressor_id", "best_bid", "best_ask"]


class Order:
    __slots__ = ("order_id", "agent_id", "side", "price", "qty", "time")

    def __init__(self, order_id, agent_id, side, price, qty, time):
        self.order_id = order_id
        self.agent_id = agent_id
        self.side = side
        self.price = price
        self.qty = qty
        self.time = time


class OrderBook:
    def __init__(self):
        self.levels = {BUY: {}, SELL: {}}   # side -> {price: queue of Orders, oldest first}
        self.orders = {}                    # order_id -> resting Order
        self.next_id = 1
        self.log = []

    # --- looking at the book ---------------------------------------------------
    def best(self, side):
        prices = self.levels[side]
        if not prices:
            return None
        return max(prices) if side == BUY else min(prices)

    def best_bid(self):
        return self.best(BUY)

    def best_ask(self):
        return self.best(SELL)

    def mid(self):
        bid, ask = self.best_bid(), self.best_ask()
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2

    def depth(self, side, n_levels):
        """Total quantity at each of the best n price levels (padded with zeros)."""
        book_side = self.levels[side]
        prices = sorted(book_side, reverse=(side == BUY))[:n_levels]
        sizes = [sum(order.qty for order in book_side[p]) for p in prices]
        return sizes + [0] * (n_levels - len(sizes))

    def imbalance(self, n_levels):
        """(bid depth - ask depth) / (bid depth + ask depth): +1 all bids, -1 all asks."""
        bids = sum(self.depth(BUY, n_levels))
        asks = sum(self.depth(SELL, n_levels))
        return 0.0 if bids + asks == 0 else (bids - asks) / (bids + asks)

    # --- changing the book -----------------------------------------------------
    def submit(self, agent_id, side, price, qty, time):
        """Submit a limit order. Returns its order_id if any of it rests, else None."""
        opposite = self.levels[-side]
        while qty > 0 and opposite:
            best = self.best(-side)
            crosses = best <= price if side == BUY else best >= price
            if not crosses:
                break
            queue = opposite[best]
            resting = queue[0]
            fill = min(qty, resting.qty)
            self._record(time, "TRADE", resting, fill, aggressor_id=agent_id)
            resting.qty -= fill
            qty -= fill
            if resting.qty == 0:
                queue.popleft()
                del self.orders[resting.order_id]
                if not queue:
                    del opposite[best]

        if qty == 0:
            return None
        order = Order(self.next_id, agent_id, side, price, qty, time)
        self.next_id += 1
        self._record(time, "ADD", order, qty)
        self.levels[side].setdefault(price, deque()).append(order)
        self.orders[order.order_id] = order
        return order.order_id

    def cancel(self, order_id, time):
        """Cancel a resting order. Returns False if it has already gone (filled)."""
        order = self.orders.get(order_id)
        if order is None:
            return False
        self._record(time, "CANCEL", order, order.qty)
        del self.orders[order_id]
        queue = self.levels[order.side][order.price]
        queue.remove(order)
        if not queue:
            del self.levels[order.side][order.price]
        return True

    def _record(self, time, kind, order, qty, aggressor_id=-1):
        self.log.append((time, kind, order.order_id, order.agent_id, order.side,
                         order.price, qty, order.time, aggressor_id,
                         self.best_bid(), self.best_ask()))
