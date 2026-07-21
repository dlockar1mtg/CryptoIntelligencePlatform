from crypto_platform.platform import load_all, connect
from crypto_platform.module29 import MODULE29_SCHEMA


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
    conn.execute(MODULE29_SCHEMA)

    show(conn, "RESEARCH SUMMARY", """
        SELECT *
        EXCLUDE(run_id, calculated_at_utc)
        FROM latest_m29_research_summary
    """)

    show(conn, "STABLE FEATURE REGISTRY", """
        SELECT feature_key,
               source_group,
               evidence_grade,
               permutation_importance_mean,
               permutation_importance_std,
               positive_importance_fold_rate_pct,
               bootstrap_selection_rate_pct,
               rolling_positive_rate_pct,
               regime_separation_score,
               redundancy_penalty,
               ablation_delta_pct,
               stability_score,
               composite_evidence_score,
               selection_rank
        FROM latest_m29_feature_registry
        WHERE stable_feature=TRUE
        ORDER BY selection_rank
    """)

    show(conn, "REJECTED FEATURES", """
        SELECT feature_key,
               source_group,
               evidence_grade,
               stability_score,
               composite_evidence_score,
               positive_importance_fold_rate_pct,
               bootstrap_selection_rate_pct,
               rolling_positive_rate_pct,
               ablation_delta_pct
        FROM latest_m29_feature_registry
        WHERE stable_feature=FALSE
        ORDER BY composite_evidence_score DESC
    """)

    show(conn, "MINIMAL MODEL COMPARISON", """
        SELECT model_key,
               feature_count,
               test_rows,
               walk_forward_accuracy_pct,
               mean_fold_accuracy_pct,
               worst_fold_accuracy_pct,
               best_fold_accuracy_pct,
               feature_list
        FROM latest_m29_minimal_model_validation
    """)

    show(conn, "TOP WALK-FORWARD FEATURES", """
        SELECT feature_key,
               COUNT(*) AS folds,
               AVG(permutation_importance)
                   AS mean_importance,
               STDDEV_SAMP(permutation_importance)
                   AS importance_std,
               AVG(CASE
                   WHEN permutation_importance>0
                   THEN 1 ELSE 0 END)*100
                   AS positive_fold_rate_pct,
               AVG(ablation_delta_pct)
                   AS mean_ablation_delta_pct
        FROM latest_m29_walk_forward_importance
        GROUP BY feature_key
        ORDER BY mean_importance DESC
        LIMIT 20
    """)

    show(conn, "BOOTSTRAP STABILITY", """
        SELECT feature_key,
               bootstrap_iterations,
               selected_iterations,
               selection_rate_pct,
               importance_mean,
               importance_std,
               positive_importance_rate_pct
        FROM latest_m29_bootstrap_stability
        ORDER BY selection_rate_pct DESC
        LIMIT 20
    """)

    show(conn, "REGIME-SPECIFIC DRIVERS", """
        SELECT regime,
               feature_key,
               observations,
               standardized_mean_difference,
               within_regime_variability,
               regime_separation_score
        FROM latest_m29_regime_feature_importance
        QUALIFY ROW_NUMBER() OVER(
            PARTITION BY regime
            ORDER BY regime_separation_score DESC
        ) <= 5
    """)

    show(conn, "LATEST RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               candidate_features,
               stable_features,
               walk_forward_folds,
               bootstrap_iterations,
               rolling_windows,
               stable_core_features,
               stable_representation_features,
               validation_status,
               notes
        FROM module29_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()


if __name__ == "__main__":
    main()
