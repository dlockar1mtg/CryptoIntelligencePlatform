from crypto_platform.platform import load_all, connect
from crypto_platform.module19 import MODULE19_SCHEMA

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
    conn.execute(MODULE19_SCHEMA)

    show(conn, "FEATURE REGISTRY", """
        SELECT feature_key, feature_class,
               source_type, production_eligible,
               registry_status, active_window_days,
               active_window_coverage_pct,
               best_absolute_spearman,
               rolling_windows,
               rolling_sign_consistency_pct,
               mean_testing_spearman,
               stable_regime_count,
               best_permutation_importance,
               promotion_score,
               promotion_reason
        FROM latest_feature_registry
    """)

    show(conn, "PRODUCTION FEATURE CANDIDATES", """
        SELECT feature_key, registry_status,
               promotion_score,
               rolling_sign_consistency_pct,
               stable_regime_count,
               best_permutation_importance,
               promotion_reason
        FROM production_feature_candidates
    """)

    show(conn, "GROUPED PERMUTATION IMPORTANCE", """
        SELECT feature_group,
               forward_horizon_days,
               feature_key,
               training_rows, testing_rows,
               base_r2, importance_mean,
               importance_std, importance_rank
        FROM latest_grouped_permutation_importance
    """)

    show(conn, "ROLLING OUT-OF-SAMPLE SUMMARY", """
        SELECT feature_key,
               forward_horizon_days,
               COUNT(*) AS windows,
               AVG(testing_spearman)
                   AS mean_testing_spearman,
               AVG(
                   CASE WHEN sign_consistent
                        THEN 1 ELSE 0 END
               ) * 100 AS sign_consistency_pct,
               AVG(testing_directional_hit_rate_pct)
                   AS mean_hit_rate_pct,
               AVG(testing_top_minus_bottom_pct)
                   AS mean_top_minus_bottom_pct
        FROM latest_feature_rolling_validation
        GROUP BY feature_key,
                 forward_horizon_days
        ORDER BY ABS(
            AVG(testing_spearman)
        ) DESC
    """)

    show(conn, "REFRESHED FEATURE VALIDATION", """
        SELECT feature_key,
               forward_horizon_days,
               sample_count,
               pearson_correlation,
               spearman_correlation,
               top_minus_bottom_pct,
               directional_hit_rate_pct
        FROM latest_feature_validation_refreshed
        LIMIT 40
    """)

    show(conn, "LATEST MODULE 19 RUNS", """
        SELECT started_at_utc,
               completed_at_utc,
               status,
               refreshed_validation_rows,
               rolling_validation_rows,
               grouped_permutation_rows,
               registry_rows,
               promoted_features,
               demoted_features,
               notes
        FROM module19_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()

if __name__ == "__main__":
    main()
