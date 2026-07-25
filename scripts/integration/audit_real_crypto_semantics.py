"""Audit real recommendation and risk units before universal export."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import duckdb


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[2]
)

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(REPOSITORY_ROOT),
    )

ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    ROOT
    / "data"
    / "crypto_intelligence.duckdb"
)

OUTPUT_PATH = (
    ROOT
    / "docs"
    / "integration"
    / "universal"
    / "real_database_semantic_audit.json"
)


def rows_as_dicts(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    parameters: list[Any] | None = None,
) -> list[dict[str, Any]]:
    cursor = connection.execute(
        query,
        parameters or [],
    )

    columns = [
        item[0]
        for item in cursor.description
    ]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def main() -> None:
    connection = duckdb.connect(
        str(DATABASE_PATH),
        read_only=True,
    )

    try:
        module36_run = connection.execute(
            """
            SELECT run_id
            FROM module36_runs
            WHERE UPPER(status) = 'SUCCESS'
              AND completed_at_utc IS NOT NULL
            ORDER BY completed_at_utc DESC
            LIMIT 1
            """
        ).fetchone()[0]

        module42_run = connection.execute(
            """
            SELECT run_id
            FROM module42_runs
            WHERE UPPER(status) = 'SUCCESS'
              AND completed_at_utc IS NOT NULL
            ORDER BY completed_at_utc DESC
            LIMIT 1
            """
        ).fetchone()[0]

        recommendations = rows_as_dicts(
            connection,
            """
            SELECT
                asset_id,
                best_action,
                investment_score,
                best_current_portfolio_pct,
                weight_change_pct,
                conviction,
                forecast_confidence,
                reliability_score,
                risk_score,
                evidence_status
            FROM m42_asset_recommendations
            WHERE run_id = ?
            ORDER BY asset_id
            """,
            [module42_run],
        )

        risks = rows_as_dicts(
            connection,
            """
            SELECT
                asset_id,
                risk_status,
                annualized_volatility_pct,
                var_95_pct,
                cvar_95_pct,
                max_drawdown_365d_pct,
                liquidity_score,
                marginal_risk_contribution_pct,
                target_weight
            FROM m36_asset_risk
            WHERE run_id = ?
            ORDER BY asset_id
            """,
            [module36_run],
        )

        allocations = rows_as_dicts(
            connection,
            """
            SELECT
                asset_id,
                original_weight,
                volatility_adjusted_weight,
                final_risk_weight,
                risk_reduction_pct,
                action
            FROM m36_risk_adjusted_allocations
            WHERE run_id = ?
            ORDER BY asset_id
            """,
            [module36_run],
        )

    finally:
        connection.close()

    recommendation_weight_sum = sum(
        float(row["best_current_portfolio_pct"])
        for row in recommendations
        if row["best_current_portfolio_pct"]
        is not None
    )

    allocation_weight_sums = {
        "original_weight": sum(
            float(row["original_weight"])
            for row in allocations
            if row["original_weight"] is not None
        ),
        "volatility_adjusted_weight": sum(
            float(row["volatility_adjusted_weight"])
            for row in allocations
            if row["volatility_adjusted_weight"]
            is not None
        ),
        "final_risk_weight": sum(
            float(row["final_risk_weight"])
            for row in allocations
            if row["final_risk_weight"] is not None
        ),
    }

    payload = {
        "module36_run_id": str(module36_run),
        "module42_run_id": str(module42_run),
        "recommendation_weight_sum": (
            recommendation_weight_sum
        ),
        "allocation_weight_sums": (
            allocation_weight_sums
        ),
        "recommendations": recommendations,
        "risk_metrics": risks,
        "risk_adjusted_allocations": allocations,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
            default=str,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("Recommendation source values:")
    for row in recommendations:
        print(
            f"- {row['asset_id']}: "
            f"target={row['best_current_portfolio_pct']}, "
            f"risk_score={row['risk_score']}, "
            f"action={row['best_action']}"
        )

    print()
    print(
        "Recommendation target sum: "
        f"{recommendation_weight_sum}"
    )

    print()
    print("Module 36 risk values:")
    for row in risks:
        print(
            f"- {row['asset_id']}: "
            f"status={row['risk_status']}, "
            f"volatility={row['annualized_volatility_pct']}, "
            f"target_weight={row['target_weight']}"
        )

    print()
    print("Allocation sums:")
    for name, value in allocation_weight_sums.items():
        print(f"- {name}: {value}")

    print()
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()