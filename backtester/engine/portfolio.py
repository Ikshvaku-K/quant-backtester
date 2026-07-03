"""Tracks positions and cash, turns signals into orders, and marks the
book to market on every bar to build the equity curve.

Simplification: orders are sized and filled using the same bar's close
price that produced the signal (not the next bar's open). This is a
common shortcut in simple backtesters but is slightly optimistic —
production systems should fill at the next available price.
"""

import pandas as pd

from backtester.events import EventType, OrderEvent


class Portfolio:
    def __init__(
        self,
        data_handler,
        events_queue,
        start_date,
        initial_capital=100000.0,
        position_size_pct=1.0,
    ):
        """
        position_size_pct: fraction of available cash to deploy on each
            LONG signal (1.0 = go all-in on a single position at a time).
        """
        self.data_handler = data_handler
        self.events_queue = events_queue
        self.symbol_list = data_handler.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct

        self.current_positions = {symbol: 0 for symbol in self.symbol_list}
        self.current_holdings = self._construct_current_holdings()
        self.all_positions = []
        self.all_holdings = []
        self.trade_log = []
        self.equity_curve = None

    def _construct_current_holdings(self):
        holdings = {symbol: 0.0 for symbol in self.symbol_list}
        holdings["cash"] = self.initial_capital
        holdings["commission"] = 0.0
        holdings["total"] = self.initial_capital
        return holdings

    def update_timeindex(self, event):
        if event.type != EventType.MARKET:
            return

        latest_datetime = None
        position_snapshot = dict(self.current_positions)
        holdings_snapshot = {symbol: 0.0 for symbol in self.symbol_list}
        holdings_snapshot["cash"] = self.current_holdings["cash"]
        holdings_snapshot["commission"] = self.current_holdings["commission"]
        holdings_snapshot["total"] = self.current_holdings["cash"]

        for symbol in self.symbol_list:
            dt = self.data_handler.get_latest_bar_datetime(symbol)
            if dt is not None:
                latest_datetime = dt
            price = self.data_handler.get_latest_bar_value(symbol, "close")
            market_value = self.current_positions[symbol] * price if price is not None else 0.0
            holdings_snapshot[symbol] = market_value
            holdings_snapshot["total"] += market_value
            self.current_holdings[symbol] = market_value

        position_snapshot["datetime"] = latest_datetime
        holdings_snapshot["datetime"] = latest_datetime
        self.current_holdings["total"] = holdings_snapshot["total"]

        self.all_positions.append(position_snapshot)
        self.all_holdings.append(holdings_snapshot)

    def update_signal(self, event):
        if event.type != EventType.SIGNAL:
            return
        order = self._generate_order(event)
        if order is not None:
            self.events_queue.put(order)

    def _generate_order(self, signal):
        symbol = signal.symbol
        cur_quantity = self.current_positions[symbol]
        price = self.data_handler.get_latest_bar_value(symbol, "close")
        if price is None or price <= 0:
            return None

        if signal.signal_type == "LONG" and cur_quantity == 0:
            cash_to_deploy = self.current_holdings["cash"] * self.position_size_pct
            quantity = int(cash_to_deploy // price)
            if quantity <= 0:
                return None
            return OrderEvent(symbol, "MKT", quantity, "BUY")

        if signal.signal_type == "EXIT" and cur_quantity > 0:
            return OrderEvent(symbol, "MKT", cur_quantity, "SELL")

        return None

    def update_fill(self, event):
        if event.type != EventType.FILL:
            return

        direction = 1 if event.direction == "BUY" else -1
        self.current_positions[event.symbol] += direction * event.quantity

        cost = direction * event.fill_price * event.quantity
        self.current_holdings["cash"] -= cost + event.commission
        self.current_holdings["commission"] += event.commission

        self.trade_log.append(
            {
                "datetime": event.timestamp,
                "symbol": event.symbol,
                "direction": event.direction,
                "quantity": event.quantity,
                "price": event.fill_price,
                "commission": event.commission,
            }
        )

    def create_equity_curve_dataframe(self):
        if not self.all_holdings:
            raise ValueError(
                "No bars were processed — check the symbol and date range."
            )
        curve = pd.DataFrame(self.all_holdings)
        curve.set_index("datetime", inplace=True)
        curve["returns"] = curve["total"].pct_change().fillna(0.0)
        curve["equity_curve"] = (1.0 + curve["returns"]).cumprod()
        self.equity_curve = curve
        return curve
