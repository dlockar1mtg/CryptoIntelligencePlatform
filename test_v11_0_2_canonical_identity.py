from crypto_platform.platform import load_all, connect
from crypto_platform.module40 import MODULE40_SCHEMA

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE40_SCHEMA)

    duplicates = conn.execute("""
        SELECT COUNT(*) FROM(
            SELECT forecast_date,asset_id,horizon_days,COUNT(*) n
            FROM m40_forecast_memory
            GROUP BY forecast_date,asset_id,horizon_days
            HAVING COUNT(*)>1
        )
    """).fetchone()[0]
    forecast_count = conn.execute(
        "SELECT COUNT(*) FROM m40_forecast_memory"
    ).fetchone()[0]
    distinct_events = conn.execute("""
        SELECT COUNT(*) FROM(
            SELECT DISTINCT forecast_date,asset_id,horizon_days
            FROM m40_forecast_memory
        )
    """).fetchone()[0]
    orphan_models = conn.execute("""
        SELECT COUNT(*)
        FROM m40_model_memory c
        LEFT JOIN m40_forecast_memory p USING(forecast_memory_id)
        WHERE p.forecast_memory_id IS NULL
    """).fetchone()[0]
    orphan_attributions = conn.execute("""
        SELECT COUNT(*)
        FROM m40_attribution_memory c
        LEFT JOIN m40_forecast_memory p USING(forecast_memory_id)
        WHERE p.forecast_memory_id IS NULL
    """).fetchone()[0]
    index_row = conn.execute("""
        SELECT sql FROM duckdb_indexes()
        WHERE index_name='ux_m40_canonical_forecast'
    """).fetchone()
    conn.close()

    assert duplicates == 0, duplicates
    assert forecast_count == distinct_events, (forecast_count, distinct_events)
    assert orphan_models == 0, orphan_models
    assert orphan_attributions == 0, orphan_attributions
    assert index_row is not None
    normalized = index_row[0].lower().replace('"','').replace(' ','')
    assert "forecast_date,asset_id,horizon_days" in normalized
    assert "model_version" not in normalized

    print("v11.0.2 canonical forecast identity preflight passed.")
    print(f"Forecast rows: {forecast_count}")
    print(f"Distinct prediction events: {distinct_events}")
    print(f"Canonical duplicates: {duplicates}")
    print(f"Orphan model rows: {orphan_models}")
    print(f"Orphan attribution rows: {orphan_attributions}")

if __name__ == "__main__":
    main()
