from crypto_platform.platform import load_all, connect, path_for

def display(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    try:
        print(conn.execute(sql).fetchdf().to_string(index=False))
    except Exception as exc:
        print(f"Unable to display: {exc}")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    display(conn, "LATEST RUNS", '''
        SELECT started_at_utc, completed_at_utc, status, platform_version,
               successful_collectors, failed_collectors, rows_received,
               rows_inserted, rows_updated
        FROM collection_runs ORDER BY started_at_utc DESC LIMIT 10
    ''')
    display(conn, "PROVIDER HEALTH", '''
        SELECT provider_group, provider_name, status, latency_ms,
               consecutive_failures, endpoint, error_message
        FROM current_provider_health
        ORDER BY provider_group, provider_name
    ''')
    display(conn, "LATEST MARKET", '''
        SELECT asset_id, observation_date, price_usd, market_cap_usd,
               volume_24h_usd, market_cap_rank, ath_change_pct, source
        FROM latest_asset_market
        ORDER BY market_cap_usd DESC NULLS LAST
    ''')
    display(conn, "OHLCV COVERAGE", '''
        SELECT asset_id, exchange, symbol, MIN(open_time_utc) first_time,
               MAX(open_time_utc) latest_time, COUNT(*) row_count
        FROM asset_ohlcv
        GROUP BY asset_id, exchange, symbol
        ORDER BY asset_id, exchange
    ''')
    display(conn, "LATEST MACRO", '''
        SELECT m.series_key, c.series_name, m.observation_date, m.value,
               m.source, c.unit
        FROM latest_macro_observations m
        LEFT JOIN macro_series_catalog c USING(series_key)
        ORDER BY m.series_key
    ''')
    display(conn, "RECENT FAILURES", '''
        SELECT collector_name, provider_name, entity_key, duration_seconds,
               error_type, error_message
        FROM collection_results
        WHERE status='FAILED'
          AND run_id = (
              SELECT run_id FROM collection_runs
              ORDER BY started_at_utc DESC LIMIT 1
          )
        ORDER BY completed_at_utc DESC LIMIT 25
    ''')
    display(conn, "PRICE CROSSCHECK", '''
        SELECT * FROM asset_price_crosscheck
        ORDER BY observation_date DESC, deviation_pct DESC LIMIT 30
    ''')
    conn.close()

if __name__ == "__main__":
    main()
