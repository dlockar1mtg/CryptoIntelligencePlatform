from crypto_platform.platform import load_all, connect
from crypto_platform.module30 import MODULE30_SCHEMA
from crypto_platform.ml.registry import EXPERIMENT_REGISTRY_SCHEMA


def show(conn, title, sql):
    print(f"\n{title}")
    print("-" * len(title))
    frame = conn.execute(sql).fetchdf()
    print(
        frame.to_string(index=False)
        if not frame.empty
        else "No data."
    )


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(EXPERIMENT_REGISTRY_SCHEMA)
    conn.execute(MODULE30_SCHEMA)

    show(conn, "CLEAN REGIME SUMMARY", """
        SELECT observation_date,
               clean_regime,
               secondary_regime,
               clean_probability*100
                   AS clean_probability_pct,
               secondary_probability*100
                   AS secondary_probability_pct,
               confidence_level,
               model_agreement*100
                   AS model_agreement_pct,
               historical_reliability*100
                   AS historical_reliability_pct,
               feature_drift_score*100
                   AS feature_drift_score_pct,
               drift_status,
               legacy_regime,
               agrees_with_legacy,
               promotion_status
        FROM latest_clean_regime_current
    """)

    show(conn, "CURRENT REGIME PROBABILITIES", """
        SELECT regime,
               probability*100 AS probability_pct,
               probability_rank
        FROM latest_clean_probability_current
    """)

    show(conn, "PRIMARY FEATURE DRIVERS", """
        SELECT feature_key,
               feature_value,
               reference_value,
               probability_contribution*100
                   AS probability_contribution_points,
               direction,
               rank
        FROM latest_clean_feature_contributions
    """)

    show(conn, "FEATURE DRIFT", """
        SELECT feature_key,
               current_value,
               training_mean,
               training_std,
               current_z_score,
               psi,
               feature_drift_score*100
                   AS feature_drift_score_pct
        FROM latest_clean_feature_drift
    """)

    show(conn, "MODEL DISAGREEMENT DIAGNOSTICS", """
        SELECT observation_date,
               gradient_regime,
               gradient_probability*100
                   AS gradient_probability_pct,
               elastic_regime,
               elastic_probability*100
                   AS elastic_probability_pct,
               probability_agreement*100
                   AS probability_agreement_pct,
               total_variation_distance*100
                   AS total_variation_distance_pct,
               blended_regime,
               blended_probability*100
                   AS blended_probability_pct,
               disagreement_flag
        FROM latest_clean_model_disagreement
    """)

    show(conn, "LEGACY BENCHMARK", """
        SELECT test_rows,
               clean_accuracy_pct,
               legacy_self_accuracy_pct,
               clean_log_loss,
               clean_brier_score,
               current_clean_regime,
               current_legacy_regime,
               current_agreement,
               relative_status
        FROM latest_clean_legacy_benchmark
    """)

    show(conn, "WALK-FORWARD FOLDS", """
        SELECT outer_fold,
               training_start_date,
               training_end_date,
               testing_start_date,
               testing_end_date,
               test_rows,
               selected_gradient_weight,
               validation_accuracy_pct,
               test_accuracy_pct,
               test_log_loss,
               test_brier_score
        FROM latest_clean_validation_folds
    """)

    show(conn, "RECENT CLEAN REGIME HISTORY", """
        SELECT observation_date,
               actual_legacy_regime,
               clean_regime,
               secondary_regime,
               clean_probability*100
                   AS clean_probability_pct,
               confidence_level,
               model_agreement*100
                   AS model_agreement_pct,
               label_match
        FROM latest_clean_regime_history
        ORDER BY observation_date DESC
        LIMIT 30
    """)

    show(conn, "LATEST EXPERIMENT", """
        SELECT experiment_id,
               module_name,
               release_version,
               started_at_utc,
               completed_at_utc,
               status,
               feature_set_json,
               hyperparameters_json,
               validation_metrics_json,
               calibration_metrics_json,
               promotion_status,
               python_version,
               sklearn_version,
               notes
        FROM ml_experiment_registry
        ORDER BY started_at_utc DESC
        LIMIT 1
    """)

    show(conn, "LATEST MODULE 30 RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               stable_features,
               outer_folds,
               historical_rows,
               clean_accuracy_pct,
               calibrated_log_loss,
               calibrated_brier_score,
               current_regime,
               current_probability,
               confidence_level,
               model_agreement,
               drift_status,
               promotion_status,
               validation_status,
               notes
        FROM module30_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()


if __name__ == "__main__":
    main()
