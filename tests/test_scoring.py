from scoring.scoring_engine import SECTION_WEIGHTS, calculate_composite_score, score_company_sections


def test_section_weights_sum_to_one() -> None:
    assert abs(sum(SECTION_WEIGHTS.values()) - 1.0) < 1e-9


def test_composite_applies_penalty_and_low_confidence_marker() -> None:
    scores = score_company_sections(
        {
            "pe_discount_to_sector_pct": 45,
            "pb_discount_to_sector_pct": 25,
            "fcf_yield_pct": 9,
            "roe_pct": 26,
            "roce_pct": 24,
            "net_debt_ebitda": 6,
            "piotroski_score": 2,
            "rsi_14": 45,
            "beta": 1.0,
        }
    )

    result = calculate_composite_score(scores, {"net_debt_ebitda": 6, "piotroski_score": 2}, {"confidence_score": 40})

    assert result["composite_score_100"] < 100
    assert result["verdict"].endswith("*")
    assert "NET_DEBT_EBITDA_6.0x" in result["penalty_flags_applied"]
