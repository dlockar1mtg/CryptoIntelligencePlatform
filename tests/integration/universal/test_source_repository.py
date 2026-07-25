from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest

from crypto_platform.integration.universal import (
    CryptoSourceRepository,
)


def create_test_database(
    path: Path,
) -> None:
    connection = duckdb.connect(
        str(path)
    )

    try:
        connection.execute(
            """
            CREATE TABLE module39_runs (
                run_id VARCHAR,
                status VARCHAR,
                started_at_utc TIMESTAMPTZ,
                completed_at_utc TIMESTAMPTZ,
                platform_version VARCHAR
            )
            """
        )

        connection.execute(
            """
            INSERT INTO module39_runs
            VALUES
                (
                    'failed-latest',
                    'FAILED',
                    '2026-07-16T11:00:00Z',
                    '2026-07-16T11:05:00Z',
                    '8.1.1'
                ),
                (
                    'successful-old',
                    'SUCCESS',
                    '2026-07-16T09:00:00Z',
                    '2026-07-16T09:05:00Z',
                    '8.1.0'
                ),
                (
                    'successful-latest',
                    'SUCCESS',
                    '2026-07-16T10:00:00Z',
                    '2026-07-16T10:05:00Z',
                    '8.1.1'
                )
            """
        )

        connection.execute(
            """
            CREATE TABLE assets (
                asset_id VARCHAR,
                symbol VARCHAR,
                asset_name VARCHAR,
                asset_tier VARCHAR,
                portfolio_enabled BOOLEAN,
                research_enabled BOOLEAN,
                native_chain VARCHAR,
                active BOOLEAN,
                coingecko_id VARCHAR,
                created_at_utc TIMESTAMPTZ
            )
            """
        )

        connection.execute(
            """
            INSERT INTO assets
            VALUES
                (
                    'bitcoin',
                    'BTC',
                    'Bitcoin',
                    'core',
                    TRUE,
                    TRUE,
                    'bitcoin',
                    TRUE,
                    'bitcoin',
                    '2026-07-01T00:00:00Z'
                ),
                (
                    'inactive-token',
                    'OFF',
                    'Inactive Token',
                    'satellite',
                    FALSE,
                    FALSE,
                    NULL,
                    FALSE,
                    NULL,
                    '2026-07-01T00:00:00Z'
                )
            """
        )

        connection.execute(
            """
            CREATE TABLE asset_market_daily (
                asset_id VARCHAR,
                observation_date DATE,
                collected_at_utc TIMESTAMPTZ
            )
            """
        )

        connection.execute(
            """
            INSERT INTO asset_market_daily
            VALUES
                (
                    'bitcoin',
                    '2020-01-01',
                    '2026-07-15T00:00:00Z'
                )
            """
        )

        connection.execute(
            """
            CREATE TABLE asset_ohlcv (
                asset_id VARCHAR,
                open_time_utc TIMESTAMPTZ,
                collected_at_utc TIMESTAMPTZ
            )
            """
        )

        connection.execute(
            """
            INSERT INTO asset_ohlcv
            VALUES
                (
                    'bitcoin',
                    '2019-01-01T00:00:00Z',
                    '2026-07-16T00:00:00Z'
                )
            """
        )

    finally:
        connection.close()


def test_latest_successful_run(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.duckdb"

    create_test_database(database)

    repository = CryptoSourceRepository(
        database
    )

    run = repository.latest_successful_run(
        39
    )

    assert run.run_id == "successful-latest"
    assert run.status == "SUCCESS"
    assert run.platform_version == "8.1.1"


def test_unsupported_module_fails(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.duckdb"

    create_test_database(database)

    repository = CryptoSourceRepository(
        database
    )

    with pytest.raises(ValueError):
        repository.latest_successful_run(
            99
        )


def test_load_active_assets(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.duckdb"

    create_test_database(database)

    repository = CryptoSourceRepository(
        database
    )

    assets = repository.load_active_assets()

    assert len(assets) == 1

    bitcoin = assets[0]

    assert bitcoin.asset_id == "bitcoin"
    assert (
        bitcoin.first_available_date.isoformat()
        == "2019-01-01"
    )

    assert bitcoin.last_updated_at_utc == datetime(
        2026,
        7,
        16,
        tzinfo=timezone.utc,
    )

def test_ohlcv_first_date_is_interpreted_in_utc(
    tmp_path: Path,
) -> None:
    database = tmp_path / "utc-source.duckdb"

    create_test_database(database)

    repository = CryptoSourceRepository(
        database
    )

    assets = repository.load_active_assets()

    assert len(assets) == 1

    assert (
        assets[0].first_available_date.isoformat()
        == "2019-01-01"
    )