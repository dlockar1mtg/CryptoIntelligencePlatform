from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA

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
        MODULE9_SCHEMA, MODULE10_SCHEMA, MODULE11_SCHEMA,
    ]:
        conn.execute(schema)

    show(conn, "EXCHANGE SYMBOL MAP", '''
        SELECT asset_id,provider,provider_symbol,quote_currency,
               market_type,mapping_method,mapping_confidence,
               last_verified_utc
        FROM latest_symbol_map
        ORDER BY asset_id,market_type,provider
    ''')
    show(conn, "RESEARCH HISTORY QUALITY", '''
        SELECT asset_id,first_date,latest_date,row_count,
               expected_days,coverage_pct,provider_count,
               primary_provider,stale_days,quality_status
        FROM latest_history_quality
        ORDER BY coverage_pct DESC,asset_id
    ''')
    show(conn, "DERIVATIVES COLLECTION STATUS", '''
        SELECT asset_id,provider,provider_symbol,supported,
               funding_rows,open_interest_rows,status,error_message
        FROM latest_derivatives_status
        ORDER BY supported DESC,asset_id
    ''')
    show(conn, "SECTOR MARKET SNAPSHOT", '''
        SELECT sector,asset_count,total_market_cap_usd,
               total_volume_24h_usd,median_return_7d_pct,
               median_return_30d_pct,positive_30d_pct,
               market_cap_weight_pct
        FROM latest_sector_snapshot
        ORDER BY total_market_cap_usd DESC
    ''')
    show(conn, "ROBUST CALIBRATED PREDICTIONS", '''
        SELECT asset_id,raw_probability_outperform,
               calibrated_probability_outperform,
               outperform_calibration_method,
               raw_probability_positive,
               calibrated_probability_positive,
               positive_calibration_method,
               predictive_weight_raw,predictive_weight_capped,
               rules_score,calibrated_predictive_score,
               final_score,final_signal,final_confidence,
               promotion_status
        FROM latest_robust_calibrated_predictive
        ORDER BY final_score DESC
    ''')
    show(conn, "CALIBRATION REGISTRY", '''
        SELECT * FROM probability_calibration_registry
        WHERE run_id=(
            SELECT run_id FROM module11_runs
            ORDER BY started_at_utc DESC LIMIT 1
        )
    ''')
    show(conn, "LATEST MODULE 11 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,
               mapped_assets,history_rows,derivatives_rows,
               taxonomy_rows,calibrated_predictions,notes
        FROM module11_runs
        ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()

if __name__ == "__main__":
    main()
