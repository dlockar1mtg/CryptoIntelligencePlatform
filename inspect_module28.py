from crypto_platform.platform import load_all,connect
from crypto_platform.module28 import MODULE28_SCHEMA

def show(conn,title,sql):
    print(f"\n{title}\n{'-'*len(title)}")
    frame=conn.execute(sql).fetchdf()
    print(frame.to_string(index=False) if not frame.empty else "No data.")

def main():
    settings,_=load_all()
    conn=connect(settings)
    conn.execute(MODULE28_SCHEMA)

    show(conn,"RESEARCH SUMMARY","""
        SELECT * EXCLUDE(run_id,calculated_at_utc)
        FROM latest_m28_research_summary
    """)

    show(conn,"RETAINED FEATURES","""
        SELECT feature_key,source_group,
               permutation_importance,
               mutual_information_proxy,
               mean_ablation_delta_pct,
               redundancy_penalty,
               composite_score,
               selection_rank
        FROM latest_m28_feature_selection
        WHERE retained=TRUE
        ORDER BY selection_rank
    """)

    show(conn,"PRUNED FEATURES","""
        SELECT feature_key,source_group,
               composite_score,
               redundancy_penalty,
               mean_ablation_delta_pct
        FROM latest_m28_feature_selection
        WHERE retained=FALSE
        ORDER BY composite_score DESC
    """)

    show(conn,"FOLD PERFORMANCE","""
        SELECT outer_fold,testing_start_date,testing_end_date,
               test_days,retained_features,meta_candidates,
               agreement_pct,raw_calibration_mae,
               calibrated_mae,mean_confidence*100 AS confidence_pct,
               switch_rate*100 AS switch_rate_pct,
               selected_calibration
        FROM latest_m28_fold_summary
    """)

    show(conn,"SELECTED META-ENSEMBLE CANDIDATES","""
        SELECT outer_fold,generation,candidate_id,
               gmm_weight,kmeans_weight,rules_weight,
               state_space_weight,probability_temperature,
               smoothing,transition_strength,
               inner_agreement_pct,inner_calibration_mae,
               objective_score,meta_weight
        FROM latest_m28_adaptive_search
        WHERE selected_for_meta=TRUE
        ORDER BY outer_fold,meta_weight DESC
    """)

    show(conn,"CALIBRATION METHOD COMPARISON","""
        SELECT outer_fold,calibration_method,
               validation_rows,validation_mae,
               validation_brier,selected
        FROM latest_m28_calibration_comparison
        ORDER BY outer_fold,selected DESC,validation_mae
    """)

    show(conn,"ROBUSTNESS SUMMARY","""
        SELECT robustness_key,observations,
               agreement_pct,calibration_mae,
               agreement_with_primary_pct,
               current_regime,
               current_confidence*100 AS confidence_pct
        FROM latest_m28_robustness_summary
    """)

    show(conn,"LATEST RUNS","""
        SELECT started_at_utc,completed_at_utc,status,
               candidate_features,retained_features,
               adaptive_candidates,outer_folds,nested_rows,
               nested_agreement_pct,calibrated_mae,
               meta_ensemble_stability_pct,current_regime,
               current_confidence,validation_status,notes
        FROM module28_runs
        ORDER BY started_at_utc DESC
        LIMIT 10
    """)

    conn.close()

if __name__=="__main__":
    main()
