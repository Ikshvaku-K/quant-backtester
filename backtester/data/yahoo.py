"""Historical OHLCV data sourced from Yahoo Finance via yfinance, with a
local CSV cache so backtests are reproducible offline after the first run.
"""

import os
import re

import numpy as np
import pandas as pd

from backtester.data.base import DataHandler
from backtester.events import MarketEvent


class YahooDataHandler(DataHandler):
    def __init__(self, events_queue, symbol_list, start_date, end_date, cache_dir="data_cache"):
        """
        events_queue: queue.Queue the engine reads MarketEvents from
        symbol_list: list of ticker strings, e.g. ["AAPL"]
        start_date, end_date: "YYYY-MM-DD" strings (end is exclusive, per yfinance)
        cache_dir: directory for per-symbol CSV cache files
        """
        self.events_queue = events_queue
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.end_date = end_date
        self.cache_dir = cache_dir
        self.continue_backtest = True

        self.symbol_data = {}
        self.latest_symbol_data = {symbol: [] for symbol in symbol_list}

        self._load_data()
        combined_index = sorted(set().union(*[df.index for df in self.symbol_data.values()]))
        self.combined_index = pd.Index(combined_index)
        self._bar_stream = self._merged_bar_generator()

    def _cache_path(self, symbol):
        os.makedirs(self.cache_dir, exist_ok=True)
        # Sanitize the symbol before putting it in a filename: a raw value
        # like "../../foo" would otherwise let the cache file escape cache_dir
        # (path traversal) if symbols ever came from untrusted input.
        safe_symbol = re.sub(r"[^A-Za-z0-9._-]", "_", symbol).lstrip(".")
        if not safe_symbol:
            raise ValueError(f"Symbol {symbol!r} has no filesystem-safe characters.")
        fname = f"{safe_symbol}_{self.start_date}_{self.end_date}.csv"
        return os.path.join(self.cache_dir, fname)

    def _load_data(self):
        for symbol in self.symbol_list:
            path = self._cache_path(symbol)
            if os.path.exists(path):
                df = pd.read_csv(path, index_col=0, parse_dates=True)
            else:
                import yfinance as yf

                df = yf.download(
                    symbol,
                    start=self.start_date,
                    end=self.end_date,
                    auto_adjust=False,
                    progress=False,
                )
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if df.empty:
                    raise ValueError(
                        f"No data returned for '{symbol}' between {self.start_date} "
                        f"and {self.end_date}. Check the ticker and date range."
                    )
                df.to_csv(path)

            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            self.symbol_data[symbol] = df.sort_index()

    def _merged_bar_generator(self):
        for timestamp in self.combined_index:
            for symbol in self.symbol_list:
                df = self.symbol_data[symbol]
                if timestamp in df.index:
                    self.latest_symbol_data[symbol].append((timestamp, df.loc[timestamp]))
            yield timestamp

    def update_bars(self):
        try:
            next(self._bar_stream)
        except StopIteration:
            self.continue_backtest = False
        else:
            self.events_queue.put(MarketEvent())

    def get_latest_bars(self, symbol, n=1):
        return self.latest_symbol_data.get(symbol, [])[-n:]

    def get_latest_bars_values(self, symbol, val_type, n=1):
        bars = self.get_latest_bars(symbol, n)
        return np.array([bar[1][val_type] for bar in bars])

    def get_latest_bar_datetime(self, symbol):
        bars = self.get_latest_bars(symbol, 1)
        return bars[-1][0] if bars else None

    def get_latest_bar_value(self, symbol, val_type):
        bars = self.get_latest_bars(symbol, 1)
        return bars[-1][1][val_type] if bars else None
