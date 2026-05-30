import pandas as pd

from calculators.technical_calc import calculate_technical_indicators


def test_technical_indicators_compute_key_levels() -> None:
    prices = []
    for index in range(260):
        close = 100 + index * 0.5
        prices.append({"date": f"2025-01-{(index % 28) + 1:02d}", "open": close - 1, "high": close + 2, "low": close - 2, "close": close, "volume": 1000 + index})

    result = calculate_technical_indicators(pd.DataFrame(prices))

    assert result["sma50"] is not None
    assert result["sma200"] is not None
    assert result["year_high"] > result["year_low"]
    assert result["suggested_stop_loss"] < result["support_level"]
