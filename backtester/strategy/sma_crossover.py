"""Classic dual moving-average crossover strategy.

Goes long when the short-window SMA crosses above the long-window SMA,
exits when it crosses back below. No shorting.
"""

from backtester.events import EventType, SignalEvent
from backtester.strategy.base import Strategy


class SMACrossoverStrategy(Strategy):
    def __init__(
        self,
        data_handler,
        events_queue,
        symbol_list=None,
        short_window=50,
        long_window=200,
        price_field="close",
    ):
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window")

        self.data_handler = data_handler
        self.events_queue = events_queue
        self.symbol_list = symbol_list or data_handler.symbol_list
        self.short_window = short_window
        self.long_window = long_window
        self.price_field = price_field
        self.bought = {symbol: "OUT" for symbol in self.symbol_list}

    def calculate_signals(self, event):
        if event.type != EventType.MARKET:
            return

        for symbol in self.symbol_list:
            bars = self.data_handler.get_latest_bars_values(
                symbol, self.price_field, n=self.long_window
            )
            if len(bars) < self.long_window:
                continue

            short_sma = bars[-self.short_window :].mean()
            long_sma = bars.mean()
            dt = self.data_handler.get_latest_bar_datetime(symbol)

            if short_sma > long_sma and self.bought[symbol] == "OUT":
                self.events_queue.put(SignalEvent(symbol, dt, "LONG"))
                self.bought[symbol] = "LONG"
            elif short_sma < long_sma and self.bought[symbol] == "LONG":
                self.events_queue.put(SignalEvent(symbol, dt, "EXIT"))
                self.bought[symbol] = "OUT"
