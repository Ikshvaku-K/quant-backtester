"""Wires data handler, strategy, portfolio, and execution handler together
and drives the event loop.
"""

import queue

from backtester.engine.execution import SimulatedExecutionHandler
from backtester.engine.portfolio import Portfolio
from backtester.events import EventType


class Backtest:
    def __init__(
        self,
        data_handler_cls,
        strategy_cls,
        symbol_list,
        start_date,
        end_date,
        initial_capital=100000.0,
        commission_pct=0.0005,
        slippage_pct=0.0,
        position_size_pct=1.0,
        cache_dir="data_cache",
        strategy_kwargs=None,
    ):
        self.events_queue = queue.Queue()

        self.data_handler = data_handler_cls(
            self.events_queue, symbol_list, start_date, end_date, cache_dir=cache_dir
        )
        self.portfolio = Portfolio(
            self.data_handler,
            self.events_queue,
            start_date,
            initial_capital=initial_capital,
            position_size_pct=position_size_pct,
        )
        self.strategy = strategy_cls(
            self.data_handler,
            self.events_queue,
            symbol_list=symbol_list,
            **(strategy_kwargs or {}),
        )
        self.execution_handler = SimulatedExecutionHandler(
            self.events_queue,
            self.data_handler,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct,
        )

    def run(self):
        while self.data_handler.continue_backtest:
            self.data_handler.update_bars()

            while True:
                try:
                    event = self.events_queue.get(block=False)
                except queue.Empty:
                    break

                if event.type == EventType.MARKET:
                    self.portfolio.update_timeindex(event)
                    self.strategy.calculate_signals(event)
                elif event.type == EventType.SIGNAL:
                    self.portfolio.update_signal(event)
                elif event.type == EventType.ORDER:
                    self.execution_handler.execute_order(event)
                elif event.type == EventType.FILL:
                    self.portfolio.update_fill(event)

        return self.portfolio.create_equity_curve_dataframe()
