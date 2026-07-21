from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    for schema in [
        MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA,
        MODULE6_SCHEMA, MODULE7_SCHEMA, MODULE8_SCHEMA,
        MODULE9_SCHEMA, MODULE10_SCHEMA,
    ]:
        conn.execute(schema)

    show(conn, "RESEARCH UNIVERSE", '''
        SELECT market_cap_rank,asset_id,symbol,name,market_cap_usd,
               volume_24h_usd,price_change_7d_pct,
               price_change_30d_pct,is_core,inclusion_reason
        FROM latest_research_universe
        ORDER BY market_cap_rank
    ''')
    show(conn, "MARKET BREADTH", '''
        SELECT * FROM latest_research_breadth
    ''')
    show(conn, "LATEST DERIVATIVES FUNDING", '''
        SELECT asset_id,symbol,observation_date,average_funding_rate,
               minimum_funding_rate,maximum_funding_rate,
               funding_observations
        FROM latest_derivatives_funding
        ORDER BY ABS(average_funding_rate) DESC
    ''')
    show(conn, "CRYPTO SENTIMENT", '''
        SELECT * FROM latest_sentiment
    ''')
    show(conn, "DEFI MARKET SNAPSHOT", '''
        SELECT * FROM latest_defi_snapshot
    ''')
    show(conn, "ISOTONIC-CALIBRATED PREDICTIONS", '''
        SELECT asset_id,raw_probability_outperform,
               calibrated_probability_outperform,
               raw_probability_positive,
               calibrated_probability_positive,
               raw_predictive_weight,capped_predictive_weight,
               calibrated_predictive_score,
               calibrated_predictive_signal,
               final_score,final_signal,final_confidence,
               promotion_status
        FROM latest_calibrated_predictive
        ORDER BY final_score DESC
    ''')
    show(conn, "LATEST MODULE 10 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,
               discovered_assets,selected_assets,history_rows,
               derivative_rows,sentiment_rows,notes
        FROM module10_runs
        ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()

if __name__ == "__main__":
    main()
