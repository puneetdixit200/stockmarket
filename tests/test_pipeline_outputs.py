from pathlib import Path

import pandas as pd

from pipeline import ResearchPipeline, RunConfig
from reporting import OUTPUT_FILENAMES


def test_pipeline_writes_all_required_outputs(tmp_path: Path) -> None:
    fixture = Path("tests/fixtures/sample_companies.json")
    result = ResearchPipeline(
        RunConfig(
            mode="TEST",
            output_dir=str(tmp_path),
            db_path=str(tmp_path / "stocks.db"),
            offline_fixture=str(fixture),
        )
    ).run()

    for filename in OUTPUT_FILENAMES:
        assert (tmp_path / filename).exists(), filename
    master_scores = pd.read_csv(tmp_path / "master_scores.csv")
    dcf = pd.read_csv(tmp_path / "dcf_valuations.csv")
    assert len(master_scores) == 3
    assert {"Ticker", "CompositeScore100", "Verdict", "DataConfidence"}.issubset(master_scores.columns)
    assert {"BearDCF", "BaseDCF", "BullDCF", "WACCUsed%"}.issubset(dcf.columns)
    assert result["run_stats"]["companies_attempted"] == 3
