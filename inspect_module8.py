from crypto_platform.platform import load_all, connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA

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
    ]:
        conn.execute(schema)

    show(conn, "ENSEMBLE VALIDATION", '''
        SELECT * FROM latest_ensemble_validation
    ''')
    show(conn, "CURRENT PREDICTIVE SIGNALS", '''
        SELECT asset_id,rules_score,rules_signal,
               ml_predicted_excess_return_pct,ml_percentile_rank,
               ml_signal,ml_confidence,ensemble_score,
               ensemble_signal,ensemble_confidence,ml_weight,
               promotion_status
        FROM latest_ml_predictions
        ORDER BY ensemble_score DESC
    ''')
    show(conn, "GLOBAL ML FEATURE IMPORTANCE", '''
        SELECT feature_name,normalized_importance,
               permutation_importance,permutation_std,rank
        FROM latest_ml_feature_importance
        ORDER BY rank
    ''')
    show(conn, "LOCAL SHAP EXPLANATIONS", '''
        SELECT asset_id,rank,feature_name,feature_value,
               shap_value,direction,baseline_prediction,
               model_prediction
        FROM latest_ml_shap_explanations
        ORDER BY asset_id,rank
    ''')
    show(conn, "ML WALK-FORWARD RESULTS", '''
        SELECT fold_number,train_start,train_end,test_start,test_end,
               training_rows,test_rows,correlation,r_squared,
               mean_absolute_error,directional_accuracy_pct,
               top_quintile_return_pct,bottom_quintile_return_pct,
               top_minus_bottom_pct
        FROM latest_ml_walk_forward_results
        ORDER BY fold_number
    ''')
    show(conn, "REGIME-SPECIFIC VALIDATION", '''
        SELECT fold_number,cycle_phase,test_rows,correlation,
               mean_absolute_error,directional_accuracy_pct,
               average_actual_return_pct,average_predicted_return_pct
        FROM latest_ml_regime_validation
        ORDER BY fold_number,cycle_phase
    ''')
    show(conn, "LATEST MODULE 8 RUNS", '''
        SELECT started_at_utc,completed_at_utc,status,
               target_horizon_days,training_rows,validation_folds,
               ml_ensemble_weight,promoted,model_artifact_path,notes
        FROM module8_runs ORDER BY started_at_utc DESC LIMIT 10
    ''')
    conn.close()

if __name__ == "__main__":
    main()
