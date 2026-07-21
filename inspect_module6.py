from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    for schema in [MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA, MODULE6_SCHEMA]:
        conn.execute(schema)

    show(conn, "HISTORICAL COVERAGE", '''
        SELECT * FROM canonical_history_coverage
        ORDER BY asset_id
    ''')
    show(conn, "LATEST HISTORICAL MODEL SNAPSHOTS", '''
        SELECT asset_id,observation_date,price_usd,
               historical_overall_score,historical_signal,
               cycle_phase,valuation_label,expected_return_proxy_pct
        FROM latest_model_snapshots
        ORDER BY historical_overall_score DESC
    ''')
    show(conn, "SIGNAL VALIDATION SUMMARY", '''
        SELECT * FROM latest_signal_validation_summary
    ''')
    show(conn, "RECENT CYCLE TRANSITIONS", '''
        SELECT * FROM recent_cycle_transitions LIMIT 40
    ''')
    show(conn, "LATEST MODULE 6 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,phase,
               canonical_rows,snapshots_created,validations_created,notes
        FROM module6_runs ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()

if __name__ == "__main__":
    main()
