from src.orderbook import BUY, SELL, OrderBook


def kinds(book):
    return [event[1] for event in book.log]


def test_non_crossing_orders_rest_on_the_book():
    book = OrderBook()
    book.submit(1, BUY, 99, 5, time=0)
    book.submit(2, SELL, 101, 3, time=0)
    assert book.best_bid() == 99
    assert book.best_ask() == 101
    assert book.mid() == 100
    assert kinds(book) == ["ADD", "ADD"]


def test_crossing_order_trades_at_resting_price():
    book = OrderBook()
    book.submit(1, SELL, 101, 3, time=0)
    leftover = book.submit(2, BUY, 105, 3, time=1)
    assert leftover is None                      # fully filled, nothing rests
    trade = book.log[-1]
    assert trade[1] == "TRADE" and trade[5] == 101 and trade[6] == 3
    assert book.best_ask() is None


def test_price_then_time_priority():
    book = OrderBook()
    first = book.submit(1, SELL, 101, 2, time=0)
    second = book.submit(2, SELL, 101, 2, time=1)
    cheaper = book.submit(3, SELL, 100, 2, time=2)
    book.submit(4, BUY, 101, 3, time=3)
    trades = [e for e in book.log if e[1] == "TRADE"]
    # cheapest price first, then the oldest order at 101
    assert [t[2] for t in trades] == [cheaper, first]
    assert book.orders[first].qty == 1
    assert second in book.orders


def test_partial_fill_leaves_remainder_resting():
    book = OrderBook()
    book.submit(1, SELL, 101, 2, time=0)
    rest_id = book.submit(2, BUY, 101, 5, time=1)
    assert rest_id is not None
    assert book.orders[rest_id].qty == 3
    assert book.best_bid() == 101


def test_cancel_removes_order_and_is_logged():
    book = OrderBook()
    oid = book.submit(1, BUY, 99, 5, time=0)
    assert book.cancel(oid, time=7)
    assert book.best_bid() is None
    cancel = book.log[-1]
    assert cancel[1] == "CANCEL" and cancel[7] == 0   # order_time lets us compute lifetime
    assert not book.cancel(oid, time=8)               # can't cancel twice


def test_depth_and_imbalance():
    book = OrderBook()
    book.submit(1, BUY, 99, 4, time=0)
    book.submit(2, BUY, 99, 1, time=0)
    book.submit(3, BUY, 97, 5, time=0)
    book.submit(4, SELL, 101, 10, time=0)
    assert book.depth(BUY, 3) == [5, 5, 0]
    assert book.depth(SELL, 2) == [10, 0]
    assert book.imbalance(5) == 0.0
