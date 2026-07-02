import queue

import numpy as np

from backtester.events import MarketEvent
from backtester.strategy.sma_crossover import SMACrossoverStrategy


class FakeSeriesDataHandler:
    """Reveals one price at a time from a fixed list, like a real feed
    would reveal one bar per MarketEvent."""

    def __init__(self, symbol, prices):
        self.symbol_list = [symbol]
        self.prices = prices
        self.n_visible = 0

    def reveal_next(self):
        self.n_visible += 1

    def get_latest_bars_values(self, symbol, val_type, n=1):
        visible = self.prices[: self.n_visible]
        return np.array(visible[-n:], dtype=float)

    def get_latest_bar_datetime(self, symbol):
        return self.n_visible - 1


def test_crossover_emits_long_then_exit_at_expected_bars():
    # Hand-computed with short_window=2, long_window=3:
    # bar4 (0-indexed): short SMA(9,12)=10.5 > long SMA(6,9,12)=9  -> LONG
    # bar5: short SMA(12,5)=8.5 < long SMA(9,12,5)=8.667           -> EXIT
    prices = [10, 8, 6, 9, 12, 5, 4]
    dh = FakeSeriesDataHandler("TEST", prices)
    events_queue = queue.Queue()
    strategy = SMACrossoverStrategy(dh, events_queue, short_window=2, long_window=3)

    for _ in prices:
        dh.reveal_next()
        strategy.calculate_signals(MarketEvent())

    signals = []
    while not events_queue.empty():
        signals.append(events_queue.get_nowait())

    assert [s.signal_type for s in signals] == ["LONG", "EXIT"]
    assert [s.timestamp for s in signals] == [4, 5]


def test_no_signal_until_long_window_is_warm():
    dh = FakeSeriesDataHandler("TEST", [10, 8])
    events_queue = queue.Queue()
    strategy = SMACrossoverStrategy(dh, events_queue, short_window=2, long_window=5)

    for _ in [10, 8]:
        dh.reveal_next()
        strategy.calculate_signals(MarketEvent())

    assert events_queue.empty()


def test_rejects_short_window_not_smaller_than_long_window():
    dh = FakeSeriesDataHandler("TEST", [10])
    events_queue = queue.Queue()
    try:
        SMACrossoverStrategy(dh, events_queue, short_window=10, long_window=10)
        assert False, "expected ValueError"
    except ValueError:
        pass
