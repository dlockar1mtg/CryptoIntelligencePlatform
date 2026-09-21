from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import duckdb

from crypto_platform.production.hosted import (
    HostedThresholds,
    evaluate_hosted_database,
    build_crypto_current_price_sidecar,
    prepare_uip_delivery,
)


def _build_database(path: Path) -> None:
    conn = duckdb.connect(str(path))
    now = datetime.now(timezone.utc)
    conn.execute("CREATE TABLE collection_runs(run_id VARCHAR, completed_at_utc TIMESTAMPTZ, status VARCHAR, successful_collectors INTEGER, failed_collectors INTEGER)")
    conn.execute("INSERT INTO collection_runs VALUES ('run-1', ?, 'SUCCESS', 4, 0)", [now])
    conn.execute("CREATE TABLE provider_health(provider_name VARCHAR, provider_group VARCHAR, status VARCHAR, checked_at_utc TIMESTAMPTZ, consecutive_failures INTEGER, error_message VARCHAR)")
    conn.execute("INSERT INTO provider_health VALUES ('coingecko', 'market', 'ONLINE', ?, 0, '')", [now])
    conn.execute("CREATE VIEW latest_provider_health AS SELECT * FROM provider_health")
    conn.execute("CREATE TABLE asset_market_daily(observation_date DATE)")
    conn.execute("INSERT INTO asset_market_daily VALUES (CURRENT_DATE)")
    conn.execute(
        """
        CREATE TABLE canonical_market_daily(
            asset_id VARCHAR,
            observation_date DATE,
            price_usd DOUBLE,
            market_cap_usd DOUBLE,
            volume_24h_usd DOUBLE,
            price_source VARCHAR,
            market_cap_source VARCHAR,
            volume_source VARCHAR,
            source_priority INTEGER,
            collected_at_utc TIMESTAMPTZ,
            PRIMARY KEY(asset_id, observation_date)
        )
        """
    )
    for index, asset_id in enumerate(
        ("bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"),
        start=1,
    ):
        conn.execute(
            """
            INSERT INTO canonical_market_daily
            VALUES (?, CURRENT_DATE, ?, NULL, NULL, 'coingecko', NULL, NULL, 1, ?)
            """,
            [asset_id, float(index * 100), now],
        )
    conn.execute("CREATE TABLE macro_observations(observation_date DATE)")
    conn.execute("INSERT INTO macro_observations VALUES (CURRENT_DATE)")
    conn.close()


def test_hosted_database_passes(tmp_path: Path) -> None:
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    result = evaluate_hosted_database(database, HostedThresholds())
    assert result["status"] == "PASS"


def test_missing_database_fails(tmp_path: Path) -> None:
    result = evaluate_hosted_database(tmp_path / "missing.duckdb")
    assert result["status"] == "FAIL"


def test_prepare_uip_delivery(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    names = {
        "asset_master.csv", "forecasts.csv", "platform_status.csv",
        "portfolio_positions.csv", "recommendations.csv", "risk_metrics.csv",
        "export_manifest.csv", "package_summary.json", "validation_report.json",
    }
    for name in names:
        (package / name).write_text("{}" if name.endswith(".json") else "header\n", encoding="utf-8")
    summary = tmp_path / "run_summary.json"
    summary.write_text(json.dumps({
        "run_id": "crypto-prod-test",
        "status": "PASS",
        "universal_export": {"status": "PASS", "output_directory": str(package)},
    }), encoding="utf-8")
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    result = prepare_uip_delivery(summary, tmp_path / "delivery", database)
    assert result["status"] == "PASS"
    assert len(result["files"]) == 11
    assert result["crypto_current_price_v1"]["status"] == "CRYPTO_CURRENT_PRICE_V1_PASS"
    delivered = tmp_path / "delivery" / "crypto-prod-test"
    assert (delivered / "crypto_current_price_v1.csv").is_file()
    assert (delivered / "crypto_current_price_v1_manifest.json").is_file()
    assert (tmp_path / "delivery" / "latest.json").is_file()


def test_crypto_current_price_sidecar_exports_exact_six_asset_authority(tmp_path: Path) -> None:
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    output = tmp_path / "crypto_current_price_v1.csv"
    manifest_path = tmp_path / "crypto_current_price_v1_manifest.json"
    manifest = build_crypto_current_price_sidecar(database, output, manifest_path)
    assert manifest["status"] == "CRYPTO_CURRENT_PRICE_V1_PASS"
    assert manifest["authority_id"] == "CRYPTO_CANONICAL_MARKET_DAILY_CURRENT_PRICE_V1"
    assert manifest["row_count"] == 6
    assert manifest["forecast_input_reused_as_price_authority"] is False
    assert manifest["intraday_quote_claimed"] is False
    assert manifest["execution_authority_granted"] is False
    text = output.read_text(encoding="utf-8")
    for asset_id in ("bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"):
        assert f"crypto:{asset_id}" in text
    assert "DAILY_CANONICAL_MARKET_CLOSE" in text
    assert "CURRENT_PRICE_FOR_PORTFOLIO_VALUATION_NOT_EXECUTION_QUOTE" in text


def test_crypto_current_price_sidecar_fails_closed_when_asset_is_missing(tmp_path: Path) -> None:
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    connection = duckdb.connect(str(database))
    connection.execute("DELETE FROM canonical_market_daily WHERE asset_id='avalanche'")
    connection.close()
    try:
        build_crypto_current_price_sidecar(
            database,
            tmp_path / "prices.csv",
            tmp_path / "manifest.json",
        )
    except ValueError as exc:
        assert "asset set mismatch" in str(exc)
    else:
        raise AssertionError("missing governed Crypto asset must fail closed")


def test_crypto_current_price_sidecar_rejects_nonpositive_price(tmp_path: Path) -> None:
    database = tmp_path / "crypto.duckdb"
    _build_database(database)
    connection = duckdb.connect(str(database))
    connection.execute(
        "UPDATE canonical_market_daily SET price_usd=0 WHERE asset_id='bitcoin'"
    )
    connection.close()
    try:
        build_crypto_current_price_sidecar(
            database,
            tmp_path / "prices.csv",
            tmp_path / "manifest.json",
        )
    except ValueError as exc:
        assert "must be positive" in str(exc)
    else:
        raise AssertionError("nonpositive governed Crypto price must fail closed")
