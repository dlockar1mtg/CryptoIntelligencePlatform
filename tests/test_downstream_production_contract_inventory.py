from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_module(number: int) -> str:
    return (
        ROOT / "crypto_platform" / f"module{number}.py"
    ).read_text(encoding="utf-8")


def test_limited_research_is_not_execution_failure() -> None:
    module30 = read_module(30)
    module35 = read_module(35)
    module38 = read_module(38)

    assert "IN ('PASSED', 'LIMITED')" in module30
    assert "IN ('PASSED','LIMITED')" in module35
    assert "IN ('PASSED', 'LIMITED')" in module38


def test_module32_does_not_select_latest_unrelated_features() -> None:
    module32 = read_module(32)

    assert "clean_runs.run_id=?" in module32
    assert "clean_runs.source_module29_run_id" in module32
    assert (
        "WHERE validation_status='PASSED' "
        "ORDER BY calculated_at_utc DESC"
        not in module32
    )


def test_module37_does_not_use_dashboard_latest_views() -> None:
    module37 = read_module(37)

    prohibited = [
        "latest_clean_probability_current",
        "latest_m31_forward_return_validation",
    ]

    for item in prohibited:
        assert item not in module37
