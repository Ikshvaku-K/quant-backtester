#!/usr/bin/env python3
"""CLI entry point: run an SMA crossover backtest against Yahoo Finance data.

Example:
    python examples/run_sma_backtest.py --symbol AAPL --start 2015-01-01 --end 2024-12-31 --plot
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtester.analytics.metrics import performance_summary
from backtester.analytics.plotting import plot_equity_curve
from backtester.data.yahoo import YahooDataHandler
from backtester.engine.backtest import Backtest
from backtester.strategy.sma_crossover import SMACrossoverStrategy


def parse_args():
    parser = argparse.ArgumentParser(description="Run an SMA crossover backtest on Yahoo Finance data.")
    parser.add_argument("--symbol", default="AAPL", help="Ticker symbol (default: AAPL)")
    parser.add_argument("--start", default="2015-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2024-12-31", help="End date YYYY-MM-DD (exclusive)")
    parser.add_argument("--short-window", type=int, default=50)
    parser.add_argument("--long-window", type=int, default=200)
    parser.add_argument("--capital", type=float, default=100000.0)
    parser.add_argument("--commission-pct", type=float, default=0.0005, help="e.g. 0.0005 = 5 bps per fill")
    parser.add_argument("--slippage-pct", type=float, default=0.0)
    parser.add_argument("--position-size-pct", type=float, default=1.0, help="Fraction of cash deployed per entry")
    parser.add_argument(
        "--cache-dir",
        default=str(Path(__file__).resolve().parent.parent / "data_cache"),
        help="Where downloaded OHLCV CSVs are cached",
    )
    parser.add_argument("--plot", action="store_true", help="Save an equity curve + drawdown chart as PNG")
    parser.add_argument("--output", default=None, help="PNG path (default: <symbol>_equity_curve.png)")
    return parser.parse_args()


def main():
    args = parse_args()

    backtest = Backtest(
        data_handler_cls=YahooDataHandler,
        strategy_cls=SMACrossoverStrategy,
        symbol_list=[args.symbol],
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        commission_pct=args.commission_pct,
        slippage_pct=args.slippage_pct,
        position_size_pct=args.position_size_pct,
        cache_dir=args.cache_dir,
        strategy_kwargs={"short_window": args.short_window, "long_window": args.long_window},
    )

    equity_curve_df = backtest.run()
    stats = performance_summary(equity_curve_df, backtest.portfolio.trade_log, args.capital)

    print(f"\nSMA({args.short_window}/{args.long_window}) crossover on {args.symbol}, {args.start} to {args.end}")
    print("-" * 60)
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key:28s}: {value:,.2f}")
        else:
            print(f"{key:28s}: {value}")

    if args.plot:
        output = args.output or f"{args.symbol}_equity_curve.png"
        plot_equity_curve(
            equity_curve_df,
            title=f"{args.symbol} SMA({args.short_window}/{args.long_window}) crossover",
            save_path=output,
        )
        print(f"\nSaved chart to {output}")


if __name__ == "__main__":
    main()
