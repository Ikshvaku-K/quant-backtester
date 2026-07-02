"""Simulated broker: fills market orders at the current bar's close,
applying a flat commission percentage and optional slippage.
"""

from backtester.events import EventType, FillEvent


class SimulatedExecutionHandler:
    def __init__(self, events_queue, data_handler, commission_pct=0.0005, slippage_pct=0.0):
        self.events_queue = events_queue
        self.data_handler = data_handler
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

    def execute_order(self, event):
        if event.type != EventType.ORDER:
            return

        price = self.data_handler.get_latest_bar_value(event.symbol, "close")
        if price is None:
            return

        slippage_sign = 1 if event.direction == "BUY" else -1
        fill_price = price * (1 + slippage_sign * self.slippage_pct)
        commission = abs(fill_price * event.quantity) * self.commission_pct
        dt = self.data_handler.get_latest_bar_datetime(event.symbol)

        fill_event = FillEvent(
            timestamp=dt,
            symbol=event.symbol,
            quantity=event.quantity,
            direction=event.direction,
            fill_price=fill_price,
            commission=commission,
        )
        self.events_queue.put(fill_event)
