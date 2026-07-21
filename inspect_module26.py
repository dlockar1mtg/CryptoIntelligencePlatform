from crypto_platform.platform import load_all,connect
from crypto_platform.module26 import MODULE26_SCHEMA
def show(c,t,q):
 print(f'\n{t}\n'+('-'*len(t))); f=c.execute(q).fetchdf(); print(f.to_string(index=False) if not f.empty else 'No data.')
def main():
 s,_=load_all(); c=connect(s); c.execute(MODULE26_SCHEMA)
 show(c,'RESEARCH SUMMARY','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m26_research_summary')
 show(c,'SELECTED FEATURES','SELECT feature_key,mutual_information,univariate_agreement_pct,stability_score,redundancy_penalty,composite_score,selection_rank FROM latest_m26_feature_research WHERE selected=TRUE ORDER BY selection_rank')
 show(c,'NESTED AGREEMENT BY FOLD','SELECT outer_fold,COUNT(*) AS days,AVG(CASE WHEN label_match THEN 1 ELSE 0 END)*100 AS agreement_pct,AVG(raw_confidence)*100 AS raw_confidence_pct,AVG(calibrated_confidence)*100 AS calibrated_confidence_pct FROM latest_m26_nested_walk_forward GROUP BY outer_fold ORDER BY outer_fold')
 show(c,'SELECTED ENSEMBLE BY FOLD','SELECT outer_fold,candidate_key,gmm_weight,kmeans_weight,rule_weight,markov_weight,smoothing,inner_agreement_pct,inner_calibration_mae,objective_score FROM latest_m26_ensemble_optimization WHERE selected=TRUE ORDER BY outer_fold')
 show(c,'CALIBRATION IMPROVEMENT','SELECT confidence_bin,observations,mean_raw_confidence,mean_calibrated_confidence,observed_accuracy,raw_absolute_error,calibrated_absolute_error FROM latest_m26_probability_calibration')
 show(c,'TRANSITION MATRIX','SELECT from_regime,to_regime,transition_probability,observations FROM latest_m26_transition_matrix QUALIFY ROW_NUMBER() OVER(PARTITION BY from_regime ORDER BY transition_probability DESC)<=3')
 show(c,'SENSITIVITY RESULTS','SELECT scenario_key,feature_count,smoothing_shift,weight_shift,label_agreement_pct,current_regime,current_confidence*100 AS confidence_pct FROM latest_m26_sensitivity_results')
 show(c,'LATEST RUNS','SELECT started_at_utc,completed_at_utc,status,candidate_features,selected_features,outer_folds,nested_test_rows,nested_agreement_pct,calibrated_mae,sensitivity_stability_pct,current_regime,current_confidence,validation_status,notes FROM module26_runs ORDER BY started_at_utc DESC LIMIT 10'); c.close()
if __name__=='__main__': main()
