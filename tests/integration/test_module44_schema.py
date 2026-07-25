from __future__ import annotations

from crypto_platform.module44 import HORIZONS, MODULE44_SCHEMA
from crypto_platform.platform import connect, load_all


def test_module44_schema_contract() -> None:
    settings, _ = load_all()
    connection = connect(settings)

    try:
        connection.execute(MODULE44_SCHEMA)

        run_columns = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE lower(table_name) = 'module44_runs'
            """
        ).fetchone()[0]

        outcome_columns = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE lower(table_name) = 'm44_decision_outcomes'
            """
        ).fetchone()[0]

        summary_columns = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE lower(table_name) = 'm44_economic_value_summary'
            """
        ).fetchone()[0]
    finally:
        connection.close()

    assert run_columns == 18
    assert outcome_columns == 24
    assert summary_columns == 15
    assert HORIZONS == [7, 30, 90, 180]
