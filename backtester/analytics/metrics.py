"""Standard backtest performance statistics computed from the equity
curve and trade log produced by Portfolio.
"""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def total_return(equity_curve):
    if len(equity_curve) == 0:
        return 0.0
    return equity_curve.iloc[-1] - 1.0


def cagr(equity_curve, periods_per_year=TRADING_DAYS_PER_YEAR):
    n_periods = len(equity_curve)
    if n_periods == 0:
        return 0.0
    final_value = equity_curve.iloc[-1]
    years = n_periods / periods_per_year
    if years <= 0 or final_value <= 0:
        return 0.0
    return final_value ** (1 / years) - 1.0


def annualized_volatility(returns, periods_per_year=TRADING_DAYS_PER_YEAR):
    if len(returns) < 2:
        return 0.0
    return returns.std(ddof=1) * np.sqrt(periods_per_year)


def sharpe_ratio(returns, risk_free_rate=0.0, periods_per_year=TRADING_DAYS_PER_YEAR):
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free_rate / periods_per_year
    std = excess.std(ddof=1)
    if std == 0 or np.isnan(std):
        return 0.0
    return np.sqrt(periods_per_year) * excess.mean() / std


def drawdown_series(equity_curve):
    running_max = equity_curve.cummax()
    return equity_curve / running_max - 1.0


def max_drawdown(equity_curve):
    if len(equity_curve) == 0:
        return 0.0
    return drawdown_series(equity_curve).min()


def compute_round_trip_pnls(trade_log_df):
    """Pair each BUY with the next SELL of the same symbol (FIFO, single
    open position per symbol, matching the strategy's own position logic)
    and return realized P&L per round trip, net of commission."""
    pnls = []
    open_trade = {}
    for _, row in trade_log_df.sort_values("datetime").iterrows():
        symbol = row["symbol"]
        if row["direction"] == "BUY":
            open_trade[symbol] = row
        elif row["direction"] == "SELL" and symbol in open_trade:
            entry = open_trade.pop(symbol)
            pnl = (row["price"] - entry["price"]) * row["quantity"]
            pnl -= row["commission"] + entry["commission"]
            pnls.append(pnl)
    return pnls


def win_rate_stats(trade_log_df):
    if trade_log_df.empty:
        return {"num_trades": 0, "win_rate_pct": 0.0, "avg_trade_pnl": 0.0}
    pnls = compute_round_trip_pnls(trade_log_df)
    if not pnls:
        return {"num_trades": 0, "win_rate_pct": 0.0, "avg_trade_pnl": 0.0}
    wins = sum(1 for p in pnls if p > 0)
    return {
        "num_trades": len(pnls),
        "win_rate_pct": 100.0 * wins / len(pnls),
        "avg_trade_pnl": float(np.mean(pnls)),
    }


def performance_summary(
    equity_curve_df,
    trade_log,
    initial_capital,
    periods_per_year=TRADING_DAYS_PER_YEAR,
    risk_free_rate=0.0,
):
    if equity_curve_df.empty:
        raise ValueError("equity_curve_df is empty — did the backtest run any bars?")

    equity_curve = equity_curve_df["equity_curve"]
    returns = equity_curve_df["returns"]
    trade_df = pd.DataFrame(trade_log)

    stats = {
        "initial_capital": initial_capital,
        "final_equity": float(equity_curve_df["total"].iloc[-1]),
        "total_return_pct": float(total_return(equity_curve) * 100),
        "cagr_pct": float(cagr(equity_curve, periods_per_year) * 100),
        "annualized_volatility_pct": float(annualized_volatility(returns, periods_per_year) * 100),
        "sharpe_ratio": float(sharpe_ratio(returns, risk_free_rate, periods_per_year)),
        "max_drawdown_pct": float(max_drawdown(equity_curve) * 100),
    }
    stats.update(win_rate_stats(trade_df))
    return stats
