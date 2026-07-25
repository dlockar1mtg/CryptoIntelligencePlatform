from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from crypto_platform.integration.universal.context import (
    ExportContext,
)
from crypto_platform.integration.universal.platform_status import (
    PLATFORM_STATUS_COLUMNS,
    build_platform_status,
)
from crypto_platform.integration.universal.portfolio_positions import (
    PORTFOLIO_POSITION_COLUMNS,
    build_empty_portfolio_positions,
)
from crypto_platform.integration.universal.source_models import (
    SourceRun,
)


def test_empty_positions_are_not_inferred() -> None:
    records = build_empty_portfolio_positions()

    assert records == []

    assert PORTFOLIO_POSITION_COLUMNS == [
        "contract_version",
        "portfolio_id",
        "universal_asset_id",
        "as_of_date",
        "quantity",
        "unit_value",
        "position_value",
        "cost_basis",
        "unrealized_gain_loss",
        "current_weight",
        "target_weight",
        "minimum_weight",
        "maximum_weight",
        "monthly_allocation_amount",
        "source_platform",
        "last_updated_at_utc",
    ]


def test_platform_status_matches_v1_contract() -> None:
    context = ExportContext.create(
        source_database=Path(
            "source.duckdb"
        ),
        output_directory=Path(
            "output"
        ),
        run_id="adapter-run",
        generated_at_utc=datetime(
            2026,
            7,
            21,
            tzinfo=timezone.utc,
        ),
    )

    runs = [
        SourceRun(
            module_number=36,
            table_name="module36_runs",
            run_id="m36",
            status="SUCCESS",
            started_at_utc=datetime(
                2026,
                7,
                16,
                10,
                0,
                tzinfo=timezone.utc,
            ),
            completed_at_utc=datetime(
                2026,
                7,
                16,
                10,
                1,
                tzinfo=timezone.utc,
            ),
            platform_version="9.1.0",
        ),
        SourceRun(
            module_number=42,
            table_name="module42_runs",
            run_id="m42",
            status="SUCCESS",
            started_at_utc=datetime(
                2026,
                7,
                16,
                11,
                0,
                tzinfo=timezone.utc,
            ),
            completed_at_utc=datetime(
                2026,
                7,
                16,
                11,
                1,
                tzinfo=timezone.utc,
            ),
            platform_version="12.0.1",
        ),
    ]

    records = build_platform_status(
        context=context,
        source_runs=runs,
        exported_record_count=150,
    )

    assert PLATFORM_STATUS_COLUMNS == [
        "contract_version",
        "platform_id",
        "platform_name",
        "platform_version",
        "run_id",
        "run_started_at_utc",
        "run_completed_at_utc",
        "run_status",
        "data_as_of_date",
        "records_published",
        "warning_count",
        "error_count",
        "source_machine",
        "message",
    ]

    assert len(records) == 1

    status = records[0]

    assert status.run_status == "success"
    assert status.records_published == 150
    assert status.warning_count == 1
    assert status.source_machine is None
    assert status.run_started_at_utc == datetime(
        2026,
        7,
        16,
        10,
        0,
        tzinfo=timezone.utc,
    )
    assert status.run_completed_at_utc == datetime(
        2026,
        7,
        16,
        11,
        1,
        tzinfo=timezone.utc,
    )
    assert "RESEARCH ONLY" in status.message
    assert "holdings" in status.message.lower()
    assert "M36=m36" in status.message
    assert "M42=m42" in status.message
