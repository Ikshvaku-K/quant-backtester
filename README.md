# quant-backtester

A small event-driven backtesting engine for equity strategies, built from
scratch (no backtrader/zipline/vectorbt dependency). Data comes from Yahoo
Finance via [`yfinance`](https://github.com/ranaroussi/yfinance), a free,
open-source source of historical OHLCV data.

Ships with one working example: a dual moving-average (SMA) crossover
strategy on equities.

## Architecture

Event-driven loop, four event types flow through a single queue:

```
MarketEvent  -> Strategy.calculate_signals()  -> SignalEvent
SignalEvent  -> Portfolio.update_signal()      -> OrderEvent
OrderEvent   -> ExecutionHandler.execute_order() -> FillEvent
FillEvent    -> Portfolio.update_fill()        -> (updates cash/positions)
```

```
backtester/
  events.py           MarketEvent, SignalEvent, OrderEvent, FillEvent
  data/
    base.py           DataHandler interface
    yahoo.py           YahooDataHandler — yfinance + local CSV cache
  strategy/
    base.py           Strategy interface
    sma_crossover.py   SMACrossoverStrategy
  engine/
    portfolio.py       position sizing, cash tracking, equity curve
    execution.py        simulated fills with commission/slippage
    backtest.py          wires it all together, runs the event loop
  analytics/
    metrics.py            CAGR, Sharpe, max drawdown, win rate
    plotting.py             equity curve + drawdown chart (saved to PNG)
examples/
  run_sma_backtest.py    CLI entry point
tests/                    pytest unit tests for metrics/portfolio/strategy
data_cache/                downloaded OHLCV CSVs (gitignored, created on first run)
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Quick start

```bash
python examples/run_sma_backtest.py --symbol AAPL --start 2015-01-01 --end 2024-12-31 --plot
```

This downloads AAPL daily bars (cached to `data_cache/` after the first
run, so reruns work offline), runs a 50/200-day SMA crossover, prints a
performance summary, and saves `AAPL_equity_curve.png`.

Useful flags:

```bash
python examples/run_sma_backtest.py \
  --symbol MSFT \
  --start 2018-01-01 --end 2024-12-31 \
  --short-window 20 --long-window 100 \
  --capital 50000 \
  --commission-pct 0.0005 \
  --slippage-pct 0.0005 \
  --plot
```

## Writing your own strategy

Subclass `backtester.strategy.base.Strategy` and implement
`calculate_signals(event)`, reading price history via
`self.data_handler.get_latest_bars_values(symbol, "close", n=...)` and
pushing `SignalEvent(symbol, timestamp, "LONG" | "EXIT")` onto
`self.events_queue`. Pass your class to `Backtest(strategy_cls=...)`.

## Known simplifications

- Long-only, one position per symbol at a time, no shorting.
- Orders are sized and filled at the **same bar's close** that generated
  the signal, not the next bar's open — a common simplification in small
  backtesters, but slightly optimistic. Swap in next-open fills in
  `engine/execution.py` if you need more realism.
- Position sizing is "deploy `position_size_pct` of available cash",
  not a real risk-based sizer.
- Data is daily bars only; no corporate-action adjustments beyond what
  yfinance's `Adj Close` provides.

This is a research/education tool, not a production trading system —
validate any strategy thoroughly before risking real capital.

## Tests

```bash
pytest tests/ -v
```
