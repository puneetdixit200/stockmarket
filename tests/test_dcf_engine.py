from calculators.dcf_engine import run_dcf_engine


def test_dcf_engine_returns_three_scenarios_and_flags_estimated_gsec() -> None:
    result = run_dcf_engine(
        {
            "last_price": 100,
            "revenue_history": [1000, 1100, 1210, 1331, 1464],
            "ebit_history": [120, 140, 160, 180, 210],
            "shares_outstanding": 10,
            "net_debt": 100,
            "debt_equity": 0.2,
            "beta": 1.1,
        },
        {"gsec_10yr_yield": 7.0, "gsec_10yr_yield_source": "estimated"},
    )

    assert result["bear_dcf_value"] >= 0
    assert result["base_dcf_value"] >= result["bear_dcf_value"]
    assert result["bull_dcf_value"] >= result["base_dcf_value"]
    assert "USING_ESTIMATED_GSEC" in result["key_flags"]
