from data_collectors.indian_stock_api_collector import IndianStockAPICollector


class FailingSession:
    def get(self, *args, **kwargs):
        raise TimeoutError("network timeout")


def test_batch_timeout_does_not_retry_each_symbol(monkeypatch) -> None:
    collector = IndianStockAPICollector(session=FailingSession(), timeout=1)
    called: list[str] = []

    def fetch_stock(symbol: str):
        called.append(symbol)
        return {"symbol": symbol}

    monkeypatch.setattr(collector, "fetch_stock", fetch_stock)

    result = collector.fetch_batch(["RELIANCE", "TCS"])

    assert called == []
    assert result["RELIANCE"]["_source"] == "unavailable"
    assert result["TCS"]["_source"] == "unavailable"
