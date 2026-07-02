import queue
from datetime import datetime

from backtester.engine.portfolio import Portfolio
from backtester.events import FillEvent, SignalEvent


class FakeDataHandler:
    """Minimal stand-in exposing only what Portfolio needs."""

    def __init__(self, symbol_list):
        self.symbol_list = symbol_list
        self._price = {}
        self._dt = {}

    def set_price(self, symbol, price, dt):
        self._price[symbol] = price
        self._dt[symbol] = dt

    def get_latest_bar_value(self, symbol, val_type):
        assert val_type == "close"
        return self._price.get(symbol)

    def get_latest_bar_datetime(self, symbol):
        return self._dt.get(symbol)


def test_signal_sizes_order_from_available_cash():
    dh = FakeDataHandler(["AAPL"])
    dh.set_price("AAPL", 100.0, datetime(2020, 1, 1))
    events_queue = queue.Queue()
    portfolio = Portfolio(dh, events_queue, start_date="2020-01-01", initial_capital=10000.0)

    portfolio.update_signal(SignalEvent("AAPL", datetime(2020, 1, 1), "LONG"))

    order = events_queue.get_nowait()
    assert order.symbol == "AAPL"
    assert order.direction == "BUY"
    assert order.quantity == 100  # 10000 // 100


def test_no_order_when_cash_cannot_afford_one_share():
    dh = FakeDataHandler(["AAPL"])
    dh.set_price("AAPL", 1_000_000.0, datetime(2020, 1, 1))
    events_queue = queue.Queue()
    portfolio = Portfolio(dh, events_queue, start_date="2020-01-01", initial_capital=100.0)

    portfolio.update_signal(SignalEvent("AAPL", datetime(2020, 1, 1), "LONG"))

    assert events_queue.empty()


def test_exit_signal_only_fires_order_when_holding_position():
    dh = FakeDataHandler(["AAPL"])
    dh.set_price("AAPL", 100.0, datetime(2020, 1, 1))
    events_queue = queue.Queue()
    portfolio = Portfolio(dh, events_queue, start_date="2020-01-01", initial_capital=10000.0)

    portfolio.update_signal(SignalEvent("AAPL", datetime(2020, 1, 1), "EXIT"))
    assert events_queue.empty()

    portfolio.current_positions["AAPL"] = 50
    portfolio.update_signal(SignalEvent("AAPL", datetime(2020, 1, 1), "EXIT"))
    order = events_queue.get_nowait()
    assert order.direction == "SELL"
    assert order.quantity == 50


def test_fill_updates_cash_position_and_trade_log():
    dh = FakeDataHandler(["AAPL"])
    events_queue = queue.Queue()
    portfolio = Portfolio(dh, events_queue, start_date="2020-01-01", initial_capital=10000.0)

    fill = FillEvent(datetime(2020, 1, 1), "AAPL", 100, "BUY", 100.0, commission=5.0)
    portfolio.update_fill(fill)

    assert portfolio.current_positions["AAPL"] == 100
    assert portfolio.current_holdings["cash"] == 10000.0 - 100 * 100.0 - 5.0
    assert len(portfolio.trade_log) == 1
