from crypto_platform.platform import load_all, connect
from crypto_platform.module27 import MODULE27_SCHEMA

def show(conn, title, sql):
    print(f"\n{title}\n{'-'*len(title)}")
    frame = conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE27_SCHEMA)

    show(conn, "RESEARCH SUMMARY", """
        SELECT * EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m27_research_summary
    """)

    show(conn, "FOLD PERFORMANCE", """
        SELECT outer_fold, testing_start_date, testing_end_date,
               test_days, agreement_pct,
               mean_raw_confidence*100 AS raw_confidence_pct,
               mean_calibrated_confidence*100 AS calibrated_confidence_pct,
               switch_rate*100 AS switch_rate_pct,
               selected_candidate_id
        FROM latest_m27_fold_summary
    """)

    show(conn, "SELECTED RANDOM SEARCH CANDIDATES", """
        SELECT outer_fold, candidate_id,
               gmm_weight, kmeans_weight, rules_weight,
               state_space_weight, probability_temperature,
               smoothing, transition_strength,
               inner_agreement_pct, inner_calibration_mae,
               inner_switch_rate, objective_score
        FROM latest_m27_random_search
        WHERE selected=TRUE
        ORDER BY outer_fold
    """)

    show(conn, "CALIBRATION RESULTS", """
        SELECT confidence_bin, observations,
               mean_raw_confidence,
               mean_calibrated_confidence,
               observed_accuracy,
               raw_error, calibrated_error
        FROM latest_m27_calibration_summary
    """)

    show(conn, "EMPIRICAL SENSITIVITY", """
        SELECT scenario_key, scenario_description,
               nested_rows, agreement_pct,
               agreement_with_baseline_pct,
               calibration_mae,
               current_regime,
               current_confidence*100 AS current_confidence_pct
        FROM latest_m27_empirical_sensitivity
    """)

    show(conn, "CURRENT REPRESENTATION FEATURES", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m27_representation_features
        ORDER BY observation_date DESC
        LIMIT 1
    """)

    show(conn, "LATEST RUNS", """
        SELECT started_at_utc, completed_at_utc, status,
               representation_features, random_candidates,
               outer_folds, nested_rows,
               nested_agreement_pct, calibrated_mae,
               empirical_stability_pct,
               current_regime, current_confidence,
               validation_status, notes
        FROM module27_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()

if __name__ == "__main__":
    main()
