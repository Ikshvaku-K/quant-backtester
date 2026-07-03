# Architecture

## The route: one bar's journey through the engine

The engine is a single event loop in [`engine/backtest.py`](backtester/engine/backtest.py)
that repeats once per trading bar. Every component communicates through **one
central `queue.Queue`** — nothing calls anything else directly.

```
Backtest loop  ── advance one bar, then drain the queue ──┐
        │                                                 │
        ▼                                                 │
  DataHandler        ── emits ──▶  MarketEvent            │
        │                                                 │
        ▼                                                 │
  Strategy           ── emits ──▶  SignalEvent            │  loop:
        │                                                 │  next bar
        ▼                                                 │
  Portfolio (size)   ── emits ──▶  OrderEvent             │
        │                                                 │
        ▼                                                 │
  ExecutionHandler   ── emits ──▶  FillEvent              │
        │                                                 │
        ▼                                                 │
  Portfolio (book)   ── update cash / position / equity ──┘
```

Each pass of the loop:

1. `DataHandler.update_bars()` reveals the next bar's OHLCV row and pushes a
   `MarketEvent`. It only ever *appends* to visible history, so a strategy can
   look backward but never forward — no lookahead bias.
2. The loop drains the queue. A `MarketEvent` marks the portfolio to market
   (adds an equity-curve point) and runs the strategy.
3. On a crossover the strategy emits a `SignalEvent` — intent only ("go long"),
   no size, no price.
4. The portfolio turns intent into an `OrderEvent` — this is the only place cash,
   position limits, and sizing live.
5. The execution handler simulates the broker: applies commission/slippage and
   emits a `FillEvent`.
6. The portfolio consumes the fill, updates cash and position, and logs the trade.

Then the loop advances to the next bar.

## Layered design

Four layers, each behind an abstract interface so any one can be swapped without
touching the others:

| Layer | Interface | Concrete impl | Owns |
|-------|-----------|---------------|------|
| Data | [`DataHandler`](backtester/data/base.py) | [`YahooDataHandler`](backtester/data/yahoo.py) | bar streaming, no-lookahead guarantee, CSV cache |
| Strategy | [`Strategy`](backtester/strategy/base.py) | [`SMACrossoverStrategy`](backtester/strategy/sma_crossover.py) | reads price history, emits signals |
| Portfolio | — | [`Portfolio`](backtester/engine/portfolio.py) | sizing, cash, positions, equity curve |
| Execution | — | [`SimulatedExecutionHandler`](backtester/engine/execution.py) | commission, slippage, fills |

Swap the data subclass and every strategy runs on crypto or CSVs unchanged. Swap
the strategy subclass and it runs against the same data and frictions. That
decoupling is the entire point of the design.

## Why event-driven instead of vectorized

Most tutorial backtests compute signals as one big pandas column operation over
the whole price series at once. Fast, but it silently cheats: it's trivial to leak
future data, and it can't model an order that fails to fill or a position sized
against real available cash.

This engine processes one bar at a time, exactly as a live system would — so the
same strategy code could in principle be pointed at a live feed. That structural
honesty is the differentiator, not the SMA strategy itself (which is deliberately
the simplest possible example).

## Strategies to add next

Each is a new `Strategy` subclass and nothing else — same route, same portfolio,
same analytics:

| Strategy | What it exercises that SMA doesn't | Effort |
|----------|-----------------------------------|--------|
| Bollinger / RSI mean-reversion | Buying weakness instead of strength (inverse logic) | Low |
| Momentum / time-series (12-1) | Ranking and periodic rebalancing | Low |
| Dual momentum | Multi-asset selection and rotation | Medium |
| Pairs / stat-arb (z-score spread) | Simultaneous long+short, hedged positions | Medium-High |
| Volatility-targeted sizing | Innovation in the portfolio layer, not the signal | Medium |

Recommended order: RSI mean-reversion first (cheapest proof the framework is
strategy-agnostic), then a pairs trade (long+short accounting is where naive
backtesters break).

## Known simplifications

- Long-only, one position per symbol at a time, no shorting.
- Orders fill at the **same bar's close** that produced the signal, not the next
  bar's open — a common shortcut, but slightly optimistic.
- Position sizing is "deploy a fraction of available cash", not risk-based.
- Daily bars only; adjustments limited to what yfinance's `Adj Close` provides.

Research/education tool — validate any strategy thoroughly before risking capital.
