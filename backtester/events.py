"""Event types passed through the backtest's central event queue.

The engine is event-driven: MARKET events (a new bar arrived) trigger
strategies to emit SIGNAL events, which the portfolio turns into ORDER
events, which the execution handler turns into FILL events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventType(Enum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"


@dataclass
class MarketEvent:
    type: EventType = field(default=EventType.MARKET, init=False)


@dataclass
class SignalEvent:
    symbol: str
    timestamp: datetime
    signal_type: str  # "LONG", "SHORT", "EXIT"
    strength: float = 1.0
    type: EventType = field(default=EventType.SIGNAL, init=False)


@dataclass
class OrderEvent:
    symbol: str
    order_type: str  # "MKT"
    quantity: int
    direction: str  # "BUY" or "SELL"
    type: EventType = field(default=EventType.ORDER, init=False)


@dataclass
class FillEvent:
    timestamp: datetime
    symbol: str
    quantity: int
    direction: str  # "BUY" or "SELL"
    fill_price: float
    commission: float
    type: EventType = field(default=EventType.FILL, init=False)
