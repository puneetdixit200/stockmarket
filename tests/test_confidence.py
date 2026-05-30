from confidence.data_confidence import calculate_data_confidence


def test_confidence_scores_complete_general_company() -> None:
    data = {
        "revenue_history": [1, 2, 3, 4, 5],
        "pat_history": [1, 2, 3, 4, 5],
        "total_assets_history": [1, 2, 3, 4, 5],
        "equity_history": [1, 2, 3, 4, 5],
        "cfo_history": [1, 2, 3, 4, 5],
        "promoter_pct": 50,
        "pledge_pct": 0,
        "total_directors": 10,
        "price_history_dates": [str(day) for day in range(756)],
        "beta": 1.0,
        "sector_median_pe": 20,
        "target_mean_price": 100,
        "analyst_recommendation": "buy",
    }

    result = calculate_data_confidence(data, "GENERAL")

    assert result["confidence_score"] == 100
    assert result["confidence_grade"] == "A"
    assert result["missing_critical_fields"] == []


def test_confidence_tracks_missing_bank_metrics() -> None:
    data = {
        "revenue_history": [1, 2, 3],
        "pat_history": [1, 2, 3],
        "total_assets_history": [1, 2, 3],
        "equity_history": [1, 2, 3],
        "cfo_history": [1, 2, 3],
        "promoter_pct": 0,
        "pledge_pct": 0,
        "total_directors": 12,
        "beta": 1.0,
        "sector_median_pe": 20,
    }

    result = calculate_data_confidence(data, "BANK")

    assert result["confidence_score"] < 75
    assert any("banking_metric" in item for item in result["missing_critical_fields"])
