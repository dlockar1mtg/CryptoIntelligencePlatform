"""Read-only access to certified crypto source data."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import duckdb

from .source_models import (
    SourceAsset,
    SourceRun,
)


_MODULE_RUN_TABLES: Final[
    dict[int, str]
] = {
    36: "module36_runs",
    39: "module39_runs",
    42: "module42_runs",
}


def _quote_identifier(
    value: str,
) -> str:
    return (
        '"'
        + value.replace('"', '""')
        + '"'
    )


class CryptoSourceRepository:
    """Read-only query boundary for adapter source data."""

    def __init__(
        self,
        database_path: Path,
    ) -> None:
        resolved = database_path.resolve()

        if not resolved.exists():
            raise FileNotFoundError(
                "Crypto source database not found: "
                f"{resolved}"
            )

        if not resolved.is_file():
            raise ValueError(
                "Crypto source database must be a file: "
                f"{resolved}"
            )

        self._database_path = resolved

    @property
    def database_path(self) -> Path:
        return self._database_path

    def _connect(
        self,
    ) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(
            str(self._database_path),
            read_only=True,
        )

    def latest_successful_run(
        self,
        module_number: int,
    ) -> SourceRun:
        try:
            table_name = _MODULE_RUN_TABLES[
                module_number
            ]

        except KeyError as exc:
            raise ValueError(
                "Unsupported module number for "
                f"universal export: {module_number}"
            ) from exc

        connection = self._connect()

        try:
            row = connection.execute(
                f"""
                SELECT
                    run_id,
                    status,
                    started_at_utc,
                    completed_at_utc,
                    platform_version
                FROM {_quote_identifier(table_name)}
                WHERE UPPER(status) = 'SUCCESS'
                  AND completed_at_utc IS NOT NULL
                ORDER BY
                    completed_at_utc DESC,
                    started_at_utc DESC,
                    run_id DESC
                LIMIT 1
                """
            ).fetchone()

        finally:
            connection.close()

        if row is None:
            raise RuntimeError(
                "No completed successful run found "
                f"for Module {module_number}."
            )

        return SourceRun(
            module_number=module_number,
            table_name=table_name,
            run_id=str(row[0]),
            status=str(row[1]),
            started_at_utc=row[2],
            completed_at_utc=row[3],
            platform_version=(
                None
                if row[4] is None
                else str(row[4])
            ),
        )

    def load_active_assets(
        self,
    ) -> list[SourceAsset]:
        connection = self._connect()

        try:
            rows = connection.execute(
                """
                WITH market_history AS (
                    SELECT
                        asset_id,
                        MIN(observation_date)
                            AS first_market_date,
                        MAX(collected_at_utc)
                            AS latest_market_update
                    FROM asset_market_daily
                    GROUP BY asset_id
                ),
                ohlcv_history AS (
                    SELECT
                        asset_id,
                        MIN(
                            CAST(
                                open_time_utc
                                AT TIME ZONE 'UTC'
                                AS DATE
                            )
                        ) AS first_ohlcv_date,
                        MAX(collected_at_utc)
                            AS latest_ohlcv_update
                    FROM asset_ohlcv
                    WHERE asset_id IS NOT NULL
                    GROUP BY asset_id
                )
                SELECT
                    a.asset_id,
                    a.symbol,
                    a.asset_name,
                    a.asset_tier,
                    COALESCE(
                        a.portfolio_enabled,
                        FALSE
                    ) AS portfolio_enabled,
                    COALESCE(
                        a.research_enabled,
                        FALSE
                    ) AS research_enabled,
                    a.native_chain,
                    COALESCE(
                        a.active,
                        FALSE
                    ) AS active,
                    a.coingecko_id,
                    CASE
                        WHEN
                            mh.first_market_date
                            IS NULL
                        THEN oh.first_ohlcv_date

                        WHEN
                            oh.first_ohlcv_date
                            IS NULL
                        THEN mh.first_market_date

                        ELSE LEAST(
                            mh.first_market_date,
                            oh.first_ohlcv_date
                        )
                    END AS first_available_date,
                    COALESCE(
                        GREATEST(
                            mh.latest_market_update,
                            oh.latest_ohlcv_update
                        ),
                        mh.latest_market_update,
                        oh.latest_ohlcv_update,
                        a.created_at_utc
                    ) AS last_updated_at_utc
                FROM assets AS a
                LEFT JOIN market_history AS mh
                    ON mh.asset_id = a.asset_id
                LEFT JOIN ohlcv_history AS oh
                    ON oh.asset_id = a.asset_id
                WHERE COALESCE(
                    a.active,
                    FALSE
                ) = TRUE
                ORDER BY a.asset_id
                """
            ).fetchall()

        finally:
            connection.close()

        assets = [
            SourceAsset(
                asset_id=str(row[0]),
                symbol=(
                    None
                    if row[1] is None
                    else str(row[1])
                ),
                asset_name=str(row[2]),
                asset_tier=(
                    None
                    if row[3] is None
                    else str(row[3])
                ),
                portfolio_enabled=bool(row[4]),
                research_enabled=bool(row[5]),
                native_chain=(
                    None
                    if row[6] is None
                    else str(row[6])
                ),
                active=bool(row[7]),
                coingecko_id=(
                    None
                    if row[8] is None
                    else str(row[8])
                ),
                first_available_date=row[9],
                last_updated_at_utc=row[10],
            )
            for row in rows
        ]

        if not assets:
            raise RuntimeError(
                "No active assets were found."
            )

        return assets