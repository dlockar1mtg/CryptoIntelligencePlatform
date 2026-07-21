from crypto_platform.platform import load_all, connect
from crypto_platform.module17 import MODULE17_SCHEMA

def show(c, title, sql):
    print(f"\n{title}\n" + "-" * len(title))
    f = c.execute(sql).fetchdf()
    print(f.to_string(index=False) if not f.empty else "No data.")

def main():
    s, _ = load_all()
    c = connect(s)
    c.execute(MODULE17_SCHEMA)
    show(c, "FEATURE READINESS", """
        SELECT feature_key,first_date,latest_date,history_days,
               non_null_count,non_null_pct,best_absolute_spearman,
               readiness_status,limitation
        FROM latest_feature_readiness
    """)
    show(c, "STRONGEST FEATURE RELATIONSHIPS", """
        SELECT feature_key,forward_horizon_days,sample_count,
               pearson_correlation,spearman_correlation,
               top_quartile_forward_return_pct,
               bottom_quartile_forward_return_pct,
               top_minus_bottom_pct,directional_hit_rate_pct
        FROM latest_feature_validation
        LIMIT 30
    """)
    show(c, "LATEST FEATURE SNAPSHOT", """
        SELECT * EXCLUDE(calculated_at_utc)
        FROM crypto_features_daily
        ORDER BY observation_date DESC LIMIT 10
    """)
    show(c, "LATEST MODULE 17 RUNS", """
        SELECT started_at_utc,completed_at_utc,status,
               fear_greed_rows,manual_etf_rows,feature_rows,
               validation_rows,ready_features,notes
        FROM module17_runs
        ORDER BY started_at_utc DESC LIMIT 10
    """)
    c.close()

if __name__ == "__main__":
    main()
