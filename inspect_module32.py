from crypto_platform.platform import load_all,connect
from crypto_platform.module32 import MODULE32_SCHEMA

def show(c,title,sql):
    print(f"\n{title}\n{'-'*len(title)}")
    f=c.execute(sql).fetchdf()
    print(f.to_string(index=False) if not f.empty else "No data.")

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE32_SCHEMA)
    show(c,"VALIDATION SUMMARY","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m32_validation_summary")
    show(c,"FEATURE STABILITY","SELECT feature_key,folds,mean_absolute_contribution,contribution_std,positive_support_rate_pct,sign_flip_rate_pct,mean_rank,rank_persistence_pct,stability_score,evidence_grade FROM latest_m32_feature_stability_summary")
    show(c,"PROBABILITY DRIFT","SELECT window_end_date,window_days,observations,mean_top_probability,mean_entropy,accuracy_pct,log_loss,brier_score,switch_rate_pct,disagreement_rate_pct,probability_psi,calibration_deterioration_pct,drift_status FROM latest_m32_probability_drift LIMIT 20")
    show(c,"ROLLING RETRAINING","SELECT policy_key,retrain_interval_days,observations,retrain_count,accuracy_pct,log_loss,brier_score,switch_rate_pct,mean_top_probability,computation_score,selected FROM latest_m32_retraining_policy_validation")
    show(c,"HISTORICAL STRESS TESTS","SELECT stress_episode_id,episode_type,start_date,end_date,observations,btc_return_pct,btc_max_drawdown_pct,mean_clean_confidence,clean_switches,dominant_clean_regime,dominant_legacy_regime,regime_agreement_pct,post_30d_btc_return_pct,stress_response_score FROM latest_m32_historical_stress_validation")
    show(c,"SYNTHETIC STRESS TESTS","SELECT scenario_key,feature_key,shock_sigma,baseline_regime,stressed_regime,baseline_probability,stressed_probability,probability_change,model_agreement,monotonic_passed,response_status FROM latest_m32_synthetic_stress_validation")
    show(c,"BENCHMARK COMPARISON","SELECT strategy_key,observations,cumulative_return_pct,cagr_pct,annualized_volatility_pct,sharpe_ratio,sortino_ratio,maximum_drawdown_pct,calmar_ratio,var_95_pct,cvar_95_pct,profitable_months_pct,annualized_turnover_pct,total_transaction_cost_pct,selected FROM latest_m32_benchmark_summary")
    show(c,"LATEST RUNS","SELECT started_at_utc,completed_at_utc,status,feature_stability_rows,probability_drift_rows,retraining_policy_rows,historical_stress_rows,synthetic_stress_rows,benchmark_rows,best_retraining_policy,best_strategy,validation_status,recommendation,notes FROM module32_runs ORDER BY started_at_utc DESC LIMIT 10")
    c.close()

if __name__=="__main__":
    main()
