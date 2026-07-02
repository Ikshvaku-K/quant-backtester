"""Equity curve + drawdown chart. Only ever saves to file — never calls
plt.show() — so it works headless in CI/sandboxed environments too.
"""

import matplotlib.pyplot as plt

from backtester.analytics.metrics import drawdown_series


def plot_equity_curve(equity_curve_df, title="Backtest results", save_path=None):
    fig, axes = plt.subplots(
        2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )

    axes[0].plot(
        equity_curve_df.index, equity_curve_df["equity_curve"], label="Equity curve", color="tab:blue"
    )
    axes[0].set_ylabel("Growth of $1")
    axes[0].set_title(title)
    axes[0].legend(loc="upper left")
    axes[0].grid(alpha=0.3)

    dd = drawdown_series(equity_curve_df["equity_curve"]) * 100
    axes[1].fill_between(equity_curve_df.index, dd, 0, color="tab:red", alpha=0.4)
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].set_xlabel("Date")
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig
