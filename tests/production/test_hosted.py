from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import duckdb

from crypto_platform.production.hosted import (
    HostedThresholds,
    evaluate_hosted_database,
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
    result = prepare_uip_delivery(summary, tmp_path / "delivery")
    assert result["status"] == "PASS"
    assert len(result["files"]) == 9
    assert (tmp_path / "delivery" / "latest.json").is_file()
