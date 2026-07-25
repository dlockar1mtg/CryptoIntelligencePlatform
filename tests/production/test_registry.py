from pathlib import Path

from crypto_platform.production.registry import MODULE_REGISTRY, active_modules, retired_modules, validate_registry


ROOT = Path(__file__).resolve().parents[2]


def test_registry_covers_modules_one_through_forty_four():
    assert [spec.number for spec in MODULE_REGISTRY] == list(range(1, 45))


def test_module_four_is_formally_retired():
    retired = retired_modules()
    assert len(retired) == 1
    assert retired[0].number == 4
    assert retired[0].runner is None
    assert retired[0].required is False


def test_all_active_runners_exist():
    assert len(active_modules()) == 43
    assert validate_registry(ROOT) == []


def test_authoritative_universal_sources_are_declared():
    by_number = {spec.number: spec for spec in MODULE_REGISTRY}
    assert "calibrated_forecasts" in by_number[39].authoritative_outputs
    assert "recommendations" in by_number[42].authoritative_outputs
