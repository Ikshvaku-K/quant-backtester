"""Abstract interface all trading strategies must implement."""

from abc import ABC, abstractmethod


class Strategy(ABC):
    """Consumes MarketEvents and emits SignalEvents onto the event queue.

    A strategy must never call get_latest_bars with n beyond what it needs
    and must never peek at bars past the current MarketEvent — that's how
    lookahead bias creeps in.
    """

    @abstractmethod
    def calculate_signals(self, event):
        raise NotImplementedError
