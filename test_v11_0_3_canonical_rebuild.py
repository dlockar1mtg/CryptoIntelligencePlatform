from crypto_platform.platform import load_all, connect
from crypto_platform.module40 import MODULE40_SCHEMA


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE40_SCHEMA)

    forecast_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM m40_forecast_memory
        """
    ).fetchone()[0]

    distinct_events = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT
                forecast_date,
                asset_id,
                horizon_days
            FROM m40_forecast_memory
        )
        """
    ).fetchone()[0]

    duplicates = forecast_count - distinct_events

    orphan_models = conn.execute(
        """
        SELECT COUNT(*)
        FROM m40_model_memory child
        LEFT JOIN m40_forecast_memory parent
          ON parent.forecast_memory_id=
             child.forecast_memory_id
        WHERE parent.forecast_memory_id IS NULL
        """
    ).fetchone()[0]

    orphan_attributions = conn.execute(
        """
        SELECT COUNT(*)
        FROM m40_attribution_memory child
        LEFT JOIN m40_forecast_memory parent
          ON parent.forecast_memory_id=
             child.forecast_memory_id
        WHERE parent.forecast_memory_id IS NULL
        """
    ).fetchone()[0]

    indexes = conn.execute(
        """
        SELECT index_name, sql
        FROM duckdb_indexes()
        WHERE index_name IN(
            'ux_m40_canonical_forecast',
            'ux_m40_model_memory_key',
            'ux_m40_attribution_memory_key'
        )
        ORDER BY index_name
        """
    ).fetchdf()

    conn.close()

    assert duplicates == 0, duplicates
    assert orphan_models == 0, orphan_models
    assert orphan_attributions == 0, (
        orphan_attributions
    )
    assert len(indexes) == 3, indexes

    canonical_sql = indexes.loc[
        indexes["index_name"]
        == "ux_m40_canonical_forecast",
        "sql",
    ].iloc[0]
    normalized = (
        canonical_sql.lower()
        .replace('"', '')
        .replace(' ', '')
    )

    assert (
        "forecast_date,asset_id,horizon_days"
        in normalized
    )
    assert "model_version" not in normalized

    print(
        "v11.0.3 canonical memory rebuild "
        "preflight passed."
    )
    print(f"Forecast rows: {forecast_count}")
    print(
        f"Distinct prediction events: "
        f"{distinct_events}"
    )
    print(
        f"Canonical duplicates: "
        f"{duplicates}"
    )
    print(
        f"Orphan model rows: "
        f"{orphan_models}"
    )
    print(
        f"Orphan attribution rows: "
        f"{orphan_attributions}"
    )
    print(
        f"Persistence indexes: "
        f"{len(indexes)}"
    )


if __name__ == "__main__":
    main()
