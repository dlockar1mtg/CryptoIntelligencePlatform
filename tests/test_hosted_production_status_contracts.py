from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(relative_path: str) -> str:
    return (
        ROOT / relative_path
    ).read_text(encoding="utf-8")


def test_module30_accepts_limited_module29_registry() -> None:
    text = source("crypto_platform/module30.py")

    assert (
        "summary.validation_status "
        "IN ('PASSED', 'LIMITED')"
    ) in text
    assert "source_m29_validation_status" in text
    assert (
        "Promotion is deliberately held at OBSERVATION."
        in text
    )


def test_module32_uses_exact_governed_feature_lineage() -> None:
    text = source("crypto_platform/module32.py")

    assert "clean_runs.source_module29_run_id" in text
    assert "runs.source_module25_run_id" in text
    assert "runs.source_module27_run_id" in text
    assert "FROM m27_representation_features" in text
    assert "[self.source_m25]" in text
    assert "[self.source_m27]" in text


def test_module35_accepts_limited_module34_source() -> None:
    text = source("crypto_platform/module35.py")

    assert (
        "validation_status IN ('PASSED','LIMITED')"
        in text
    )
    assert "self.source_validation_status" in text
    assert "rec='HOLD'" in text


def test_module37_uses_source_specific_governed_inputs() -> None:
    text = source("crypto_platform/module37.py")

    assert "FROM clean_probability_current" in text
    assert "WHERE run_id=?" in text
    assert "FROM m31_forward_return_validation" in text
    assert "[self.source_m30]" in text
    assert "[self.source_m31]" in text

    assert "latest_clean_probability_current" not in text
    assert (
        "latest_m31_forward_return_validation"
        not in text
    )


def test_module38_accepts_limited_module37_source() -> None:
    text = source("crypto_platform/module38.py")

    assert (
        "validation_status IN ('PASSED', 'LIMITED')"
        in text
    )
    assert "source_m37_validation_status" in text
