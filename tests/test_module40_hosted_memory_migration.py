from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module40_source() -> str:
    return (
        ROOT / "crypto_platform" / "module40.py"
    ).read_text(encoding="utf-8")


def test_module40_runs_memory_migration_on_startup() -> None:
    text = module40_source()

    assert "self.ensure_canonical_memory_schema()" in text


def test_module40_creates_conflict_index_idempotently() -> None:
    text = module40_source()

    assert "CREATE UNIQUE INDEX IF NOT EXISTS" in text
    assert "ux_m40_canonical_forecast" in text
    assert "DROP INDEX IF EXISTS" not in text


def test_module40_index_matches_upsert_identity() -> None:
    text = module40_source()

    expected_columns = (
        "forecast_date,\n"
        "                    asset_id,\n"
        "                    horizon_days"
    )

    assert expected_columns in text
    assert "ON CONFLICT(" in text


def test_module40_migration_consolidates_children() -> None:
    text = module40_source()

    assert "m40_models_consolidated" in text
    assert "m40_attributions_consolidated" in text
    assert "survivor_id" in text


def test_module40_migration_validates_integrity() -> None:
    text = module40_source()

    assert "duplicate_count" in text
    assert "orphan_models" in text
    assert "orphan_attributions" in text
    assert 'self.conn.execute("ROLLBACK")' in text
