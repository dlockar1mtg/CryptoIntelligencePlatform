"""Regression tests for the 2026-10 audit fixes in production code (synthetic data only)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess

import duckdb
import pytest

from crypto_platform.production import orchestrator as orchestrator_module
from crypto_platform.production.hosted import (
    CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS,
    build_crypto_current_price_sidecar,
)
from crypto_platform.production.orchestrator import (
    MODULE_TIMEOUT_SECONDS,
    PipelineOptions,
    ProductionOrchestrator,
)
from crypto_platform.production.registry import ModuleSpec, ProductionStage
from tests.production.test_hosted import _build_database


def _age_asset(database: Path, asset_id: str, days: int) -> None:
    observed = datetime.now(timezone.utc).date() - timedelta(days=days)
    connection = duckdb.connect(str(database))
    connection.execute(
        "UPDATE canonical_market_daily SET observation_date=? WHERE asset_id=?",
        [observed, asset_id],
    )
    connection.close()


def _build_sidecar(tmp_path: Path, database: Path) -> dict:
    return build_crypto_current_price_sidecar(
        database,
        tmp_path / "crypto_current_price_v1.csv",
        tmp_path / "crypto_current_price_v1_manifest.json",
    )


# --- Finding 3: per-coin price age -----------------------------------------


def test_sidecar_keeps_coin_at_the_age_limit(tmp_path: Path) -> None:
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    _age_asset(database, "solana", CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS)
    manifest = _build_sidecar(tmp_path, database)
    assert manifest["row_count"] == 6
    assert manifest["excluded_assets"] == []


def test_sidecar_excludes_stale_altcoin_with_reason(tmp_path: Path) -> None:
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    _age_asset(database, "solana", CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS + 2)
    manifest = _build_sidecar(tmp_path, database)
    assert manifest["row_count"] == 5
    assert [item["asset_id"] for item in manifest["excluded_assets"]] == ["solana"]
    assert manifest["excluded_assets"][0]["age_days"] == CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS + 2
    assert "days old" in manifest["excluded_assets"][0]["reason"]
    text = (tmp_path / "crypto_current_price_v1.csv").read_text(encoding="utf-8")
    assert "crypto:solana" not in text
    assert "crypto:bitcoin" in text
    written = json.loads(
        (tmp_path / "crypto_current_price_v1_manifest.json").read_text(encoding="utf-8")
    )
    assert written["excluded_assets"] == manifest["excluded_assets"]


@pytest.mark.parametrize("asset_id", ["bitcoin", "ethereum"])
def test_sidecar_fails_when_btc_or_eth_is_stale(tmp_path: Path, asset_id: str) -> None:
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    _age_asset(database, asset_id, CRYPTO_CURRENT_PRICE_MAX_AGE_DAYS + 1)
    with pytest.raises(ValueError, match="stale for required assets"):
        _build_sidecar(tmp_path, database)


# --- Finding 5: orchestrator fallbacks -------------------------------------


def test_empty_database_env_var_uses_default_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CRYPTO_DATABASE_PATH", "")
    orchestrator = ProductionOrchestrator(
        PipelineOptions(repository_root=tmp_path, output_root=tmp_path / "runs")
    )
    result = orchestrator._run_universal_export()
    assert result["status"] == "FAIL"
    expected = (tmp_path / "data" / "crypto_intelligence.duckdb").resolve()
    assert result["reason"] == f"Source database not found: {expected}"


def test_hung_module_times_out_and_fails(tmp_path: Path, monkeypatch) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(orchestrator_module.subprocess, "run", fake_run)
    orchestrator = ProductionOrchestrator(
        PipelineOptions(repository_root=tmp_path, output_root=tmp_path / "runs")
    )
    orchestrator.logs_directory.mkdir(parents=True)
    spec = ModuleSpec(number=7, stage=ProductionStage.CORE_ANALYTICS, runner="run_module7.py")
    result = orchestrator._run_module(spec)
    assert captured["timeout"] == MODULE_TIMEOUT_SECONDS == 40 * 60
    assert result.status == "FAIL"
    assert result.return_code is None
    assert "timed out" in result.error


def test_package_validation_failure_marks_export_fail(tmp_path: Path, monkeypatch) -> None:
    from crypto_platform.integration.universal import package_builder

    database = tmp_path / "crypto.duckdb"
    database.write_bytes(b"")

    class FailingBuilder:
        def __init__(self, context):
            self.context = context

        def build(self):
            raise package_builder.PackageValidationError(
                ["recommendations_nonempty"], self.context.output_directory
            )

    import crypto_platform.integration.universal as universal

    monkeypatch.setattr(universal, "UniversalPackageBuilder", FailingBuilder)
    orchestrator = ProductionOrchestrator(
        PipelineOptions(
            repository_root=tmp_path,
            output_root=tmp_path / "runs",
            source_database=database,
        )
    )
    result = orchestrator._run_universal_export()
    assert result["status"] == "FAIL"
    assert result["failed_checks"] == ["recommendations_nonempty"]
