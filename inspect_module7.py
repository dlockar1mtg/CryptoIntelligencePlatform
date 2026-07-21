from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA

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
        MODULE6_SCHEMA, MODULE7_SCHEMA,
    ]:
        conn.execute(schema)

    show(conn, "LEARNED SIGNAL THRESHOLDS", '''
        SELECT signal_name,lower_score,upper_score,sample_count,
               expected_forward_return_pct,expected_excess_vs_btc_pct,
               positive_rate_pct,reliability_score,recommended_for_live_use
        FROM latest_learned_signal_thresholds
        ORDER BY lower_score
    ''')
    show(conn, "SCORE BIN PERFORMANCE", '''
        SELECT score_bin_low,score_bin_high,sample_count,
               average_forward_return_pct,median_forward_return_pct,
               positive_rate_pct,average_excess_vs_btc_pct,
               btc_outperformance_rate_pct,reliability_score
        FROM latest_score_bin_performance
        ORDER BY score_bin_low
    ''')
    show(conn, "FEATURE IMPORTANCE", '''
        SELECT feature_name,standardized_coefficient,direction,
               absolute_importance,permutation_importance,
               sample_count,train_r_squared
        FROM latest_feature_importance
        ORDER BY permutation_importance DESC,absolute_importance DESC
    ''')
    show(conn, "WALK-FORWARD RESULTS", '''
        SELECT fold_number,train_start,train_end,test_start,test_end,
               training_rows,test_rows,correlation,mean_absolute_error,
               directional_accuracy_pct,top_quintile_return_pct,
               bottom_quintile_return_pct,top_minus_bottom_pct
        FROM latest_walk_forward_results
        ORDER BY fold_number
    ''')
    show(conn, "HISTORICAL VALUATION VALIDATION", '''
        SELECT valuation_label,horizon_days,sample_count,
               positive_rate_pct,average_forward_return_pct,
               median_forward_return_pct,average_excess_vs_btc_pct,
               btc_outperformance_rate_pct,reliability_score
        FROM latest_valuation_validation_summary
        ORDER BY horizon_days,valuation_label
    ''')
    show(conn, "CALIBRATED SIGNAL RELIABILITY", '''
        SELECT historical_signal,horizon_days,sample_count,
               reliability_score,calibrated_confidence,
               historical_positive_rate_pct,
               historical_average_return_pct,
               historical_average_excess_pct
        FROM latest_calibrated_signal_reliability
        ORDER BY historical_signal
    ''')
    show(conn, "LATEST MODULE 7 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,
               primary_horizon_days,calibration_samples,
               walk_forward_folds,notes
        FROM module7_runs ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()

if __name__ == "__main__":
    main()
