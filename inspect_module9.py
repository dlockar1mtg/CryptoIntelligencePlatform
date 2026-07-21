from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA

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
        MODULE9_SCHEMA,
    ]:
        conn.execute(schema)

    show(conn, "PREDICTIVE PROMOTION", '''
        SELECT * FROM latest_predictive_promotion
    ''')
    show(conn, "CALIBRATED CURRENT PREDICTIONS", '''
        SELECT asset_id,cycle_phase,calibrated_excess_return_pct,
               probability_outperform_btc,probability_positive_return,
               predictive_score,predictive_signal,predictive_confidence,
               rules_score,rules_signal,final_ensemble_score,
               final_ensemble_signal,final_ensemble_confidence,
               predictive_weight,promotion_status
        FROM latest_predictive_classifications
        ORDER BY final_ensemble_score DESC
    ''')
    show(conn, "CALIBRATED WALK-FORWARD RESULTS", '''
        SELECT fold_number,train_start,train_end,test_start,test_end,
               training_rows,test_rows,regression_mae,raw_regression_mae,
               outperform_auc,positive_return_auc,
               outperform_balanced_accuracy_pct,
               positive_balanced_accuracy_pct,
               high_low_outperform_spread_pct,
               high_low_positive_spread_pct
        FROM latest_calibrated_walk_forward
        ORDER BY fold_number
    ''')
    show(conn, "PROBABILITY CALIBRATION", '''
        SELECT target_name,probability_bin_low,probability_bin_high,
               sample_count,average_predicted_probability,
               observed_rate,calibration_error
        FROM latest_probability_calibration
        ORDER BY target_name,probability_bin_low
    ''')
    show(conn, "REGIME MODEL COVERAGE", '''
        SELECT * FROM latest_regime_model_validation
        ORDER BY cycle_phase
    ''')
    show(conn, "LATEST MODULE 9 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,
               target_horizon_days,training_rows,validation_folds,
               promoted,predictive_weight,notes
        FROM module9_runs ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()

if __name__ == "__main__":
    main()
