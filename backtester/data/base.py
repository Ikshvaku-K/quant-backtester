"""Abstract interface all data sources must implement."""

from abc import ABC, abstractmethod


class DataHandler(ABC):
    """Streams historical bars to the engine one timestamp at a time.

    Concrete handlers must never leak future bars: get_latest_bars only
    exposes data up to (and including) the bar most recently pushed by
    update_bars, otherwise the backtest would have lookahead bias.
    """

    @abstractmethod
    def get_latest_bars(self, symbol: str, n: int = 1):
        """Return the last n bars for symbol as a list of (timestamp, OHLCV) rows."""
        raise NotImplementedError

    @abstractmethod
    def update_bars(self):
        """Advance the stream by one timestamp, pushing a MarketEvent."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_bar_datetime(self, symbol: str):
        raise NotImplementedError

    @abstractmethod
    def get_latest_bar_value(self, symbol: str, val_type: str):
        """val_type in {'open','high','low','close','adj_close','volume'}."""
        raise NotImplementedError
