import os

import pandas as pd
import pytest

from backtester.data.yahoo import YahooDataHandler


def _make_handler_without_download(tmp_path, symbol):
    """Build a YahooDataHandler with a pre-seeded cache file so __init__
    never hits the network, then exercise _cache_path directly."""
    handler = YahooDataHandler.__new__(YahooDataHandler)
    handler.cache_dir = str(tmp_path)
    handler.start_date = "2020-01-01"
    handler.end_date = "2020-02-01"
    return handler


def test_cache_path_stays_inside_cache_dir_for_malicious_symbol(tmp_path):
    handler = _make_handler_without_download(tmp_path, "../../etc/passwd")
    path = handler._cache_path("../../etc/passwd")
    cache_dir = os.path.realpath(str(tmp_path))
    resolved = os.path.realpath(path)
    assert resolved.startswith(cache_dir + os.sep), f"{resolved} escaped {cache_dir}"


def test_cache_path_normal_symbol_unchanged(tmp_path):
    handler = _make_handler_without_download(tmp_path, "AAPL")
    path = handler._cache_path("AAPL")
    assert os.path.basename(path) == "AAPL_2020-01-01_2020-02-01.csv"


def test_cache_path_rejects_symbol_with_no_safe_chars(tmp_path):
    # ".." would name the parent directory; after sanitizing it is empty.
    handler = _make_handler_without_download(tmp_path, "..")
    with pytest.raises(ValueError):
        handler._cache_path("..")


def test_seeded_cache_is_read_without_network(tmp_path):
    # A pre-existing cache file must be loaded as-is (no yfinance call).
    df = pd.DataFrame(
        {"Open": [10.0], "High": [11.0], "Low": [9.0], "Close": [10.5], "Adj Close": [10.5], "Volume": [100]},
        index=pd.to_datetime(["2020-01-02"]),
    )
    import queue

    events = queue.Queue()
    handler = YahooDataHandler.__new__(YahooDataHandler)
    handler.cache_dir = str(tmp_path)
    handler.start_date = "2020-01-01"
    handler.end_date = "2020-02-01"
    df.to_csv(handler._cache_path("AAPL"))

    handler.__init__(events, ["AAPL"], "2020-01-01", "2020-02-01", cache_dir=str(tmp_path))
    handler.update_bars()
    assert handler.get_latest_bar_value("AAPL", "close") == 10.5
