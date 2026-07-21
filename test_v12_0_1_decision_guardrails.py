from crypto_platform.platform import load_all, connect
from crypto_platform.module42 import MODULE42_SCHEMA


EXPECTED_RECOMMENDATION_COLUMNS = 23


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE42_SCHEMA)

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

    assert (
        recommendation_columns
        == EXPECTED_RECOMMENDATION_COLUMNS
    ), recommendation_columns
    assert projection_columns == 20, (
        projection_columns
    )

    print("v12.0.1 decision guardrail preflight passed.")
    print(
        f"recommendation columns: "
        f"{recommendation_columns}"
    )
    print(
        f"projection columns: "
        f"{projection_columns}"
    )


if __name__ == "__main__":
    main()
