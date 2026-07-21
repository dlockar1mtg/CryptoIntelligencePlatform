from crypto_platform.platform import load_all,connect
from crypto_platform.module31 import MODULE31_SCHEMA

def show(c,t,q):
    print(f"\n{t}\n{'-'*len(t)}"); f=c.execute(q).fetchdf(); print(f.to_string(index=False) if not f.empty else 'No data.')

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE31_SCHEMA)
    show(c,'RESEARCH SUMMARY','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m31_research_summary')
    show(c,'CALIBRATION COMPARISON','SELECT method,observations,multiclass_log_loss,multiclass_brier_score,top_class_mae,selected FROM latest_m31_calibration_comparison')
    show(c,'PERSISTENCE VALIDATION','SELECT method,smoothing,transition_strength,observations,accuracy_pct,log_loss,brier_score,switch_rate_pct,selected FROM latest_m31_persistence_validation LIMIT 20')
    show(c,'ECONOMIC REGIME SCORECARD','SELECT signal_source,regime,horizon_days,observations,cross_asset_return_spread_pct,risk_on_minus_btc_pct,btc_mean_return_pct,alt_mean_return_pct,positive_asset_share_pct,economic_separation_score FROM latest_m31_regime_economic_scorecard')
    show(c,'DISAGREEMENT OUTCOMES','SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m31_disagreement_outcomes')
    show(c,'GLOBAL FEATURE VALIDATION','SELECT feature_key,mean_absolute_contribution,contribution_std,positive_support_rate_pct,top_driver_rate_pct,stability_score FROM latest_m31_global_feature_validation')
    show(c,'LATEST RUNS','SELECT started_at_utc,completed_at_utc,status,historical_rows,forward_return_rows,calibration_rows,persistence_rows,investment_value_score,validation_status,recommendation,notes FROM module31_runs ORDER BY started_at_utc DESC LIMIT 10')
    c.close()
if __name__=='__main__': main()
