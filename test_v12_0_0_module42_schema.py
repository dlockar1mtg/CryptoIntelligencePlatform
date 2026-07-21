from crypto_platform.platform import load_all, connect
from crypto_platform.module42 import (
    MODULE42_SCHEMA,
    ALL_HORIZONS,
)


EXPECTED_RUN_COLUMNS = 22


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE42_SCHEMA)

    run_columns = conn.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE lower(table_name)='module42_runs'
        """
    ).fetchone()[0]

    recommendation_columns = conn.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE lower(table_name)=
              'm42_asset_recommendations'
        """
    ).fetchone()[0]

    projection_columns = conn.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE lower(table_name)=
              'm42_price_projections'
        """
    ).fetchone()[0]

    conn.close()

    assert run_columns == EXPECTED_RUN_COLUMNS, (
        run_columns
    )
    assert recommendation_columns == 24, (
        recommendation_columns
    )
    assert projection_columns == 20, (
        projection_columns
    )
    assert len(ALL_HORIZONS) == 18, (
        len(ALL_HORIZONS)
    )
    assert ALL_HORIZONS[0][0] == "7D"
    assert ALL_HORIZONS[1][0] == "30D"
    assert ALL_HORIZONS[-1][0] == "M48"

    print("v12.0.0 Module 42 schema preflight passed.")
    print(f"module42_runs columns: {run_columns}")
    print(
        f"recommendation columns: "
        f"{recommendation_columns}"
    )
    print(
        f"projection columns: "
        f"{projection_columns}"
    )
    print(
        f"projection horizons per asset: "
        f"{len(ALL_HORIZONS)}"
    )


if __name__ == "__main__":
    main()
