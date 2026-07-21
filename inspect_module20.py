from crypto_platform.platform import load_all,connect
from crypto_platform.module20 import MODULE20_SCHEMA

def show(c,title,sql):
    print(f"\n{title}\n"+'-'*len(title)); f=c.execute(sql).fetchdf(); print(f.to_string(index=False) if not f.empty else 'No data.')

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE20_SCHEMA)
    show(c,'SHADOW PORTFOLIO SUMMARY','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_shadow_portfolio_summary')
    show(c,'MODEL COMPARISON','SELECT feature_group,forward_horizon_days,model_name,training_rows,testing_rows,out_of_sample_r2,out_of_sample_mae,directional_accuracy_pct,rank_correlation,selected_model FROM latest_feature_model_comparison')
    show(c,'MODEL EXPLAINABILITY','SELECT feature_group,forward_horizon_days,model_name,feature_key,importance_mean,importance_std,importance_rank,feature_return_correlation,inferred_direction FROM latest_model_feature_explainability')
    show(c,'FEATURE REDUNDANCY','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_feature_redundancy WHERE redundancy_status=\'REDUNDANT\'')
    show(c,'EVIDENCE AGING','SELECT feature_key,prior_registry_status,aged_registry_status,prior_promotion_score,aged_promotion_score,recent_windows,recent_mean_spearman,recent_sign_consistency_pct,evidence_age_days,decay_multiplier,aging_reason FROM latest_feature_evidence_aging')
    show(c,'RECENT SHADOW PERIODS','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_shadow_portfolio_periods ORDER BY rebalance_date DESC LIMIT 18')
    show(c,'LATEST MODULE 20 RUNS','SELECT started_at_utc,completed_at_utc,status,model_rows,explainability_rows,redundancy_rows,aging_rows,shadow_periods,shadow_return_pct,btc_return_pct,shadow_excess_pct,shadow_promoted,notes FROM module20_runs ORDER BY started_at_utc DESC LIMIT 10')
    c.close()
if __name__=='__main__':main()
