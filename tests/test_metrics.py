import pandas as pd

from backtester.analytics.metrics import (
    max_drawdown,
    sharpe_ratio,
    total_return,
    win_rate_stats,
)


def test_total_return():
    equity = pd.Series([1.0, 1.1, 1.21])
    assert abs(total_return(equity) - 0.21) < 1e-9


def test_max_drawdown_known_series():
    equity = pd.Series([1.0, 1.2, 0.9, 1.1])
    # running max: [1, 1.2, 1.2, 1.2] -> drawdowns: [0, 0, -0.25, -0.0833]
    assert abs(max_drawdown(equity) - (-0.25)) < 1e-9


def test_sharpe_ratio_zero_volatility_is_zero():
    returns = pd.Series([0.01, 0.01, 0.01])
    assert sharpe_ratio(returns) == 0.0


def test_win_rate_stats_pairs_buy_sell_fifo():
    trade_log = pd.DataFrame(
        [
            {"datetime": 1, "symbol": "AAPL", "direction": "BUY", "quantity": 10, "price": 100, "commission": 1},
            {"datetime": 2, "symbol": "AAPL", "direction": "SELL", "quantity": 10, "price": 110, "commission": 1},
            {"datetime": 3, "symbol": "AAPL", "direction": "BUY", "quantity": 10, "price": 110, "commission": 1},
            {"datetime": 4, "symbol": "AAPL", "direction": "SELL", "quantity": 10, "price": 100, "commission": 1},
        ]
    )
    stats = win_rate_stats(trade_log)
    # trade 1: (110-100)*10 - 2 = 98 (win); trade 2: (100-110)*10 - 2 = -102 (loss)
    assert stats["num_trades"] == 2
    assert stats["win_rate_pct"] == 50.0
    assert abs(stats["avg_trade_pnl"] - (-2.0)) < 1e-9


def test_win_rate_stats_empty_log():
    stats = win_rate_stats(pd.DataFrame())
    assert stats["num_trades"] == 0
    assert stats["win_rate_pct"] == 0.0
