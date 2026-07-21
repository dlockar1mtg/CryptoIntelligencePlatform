from crypto_platform.platform import load_all, connect
from crypto_platform.module25_validation import MODULE25V_SCHEMA

def show(conn,title,sql):
    print(f"\n{title}\n{'-'*len(title)}")
    f=conn.execute(sql).fetchdf()
    print(f.to_string(index=False) if not f.empty else "No data.")

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE25V_SCHEMA)
    show(c,"VALIDATION SUMMARY","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m25v_validation_summary")
    show(c,"WALK-FORWARD AGREEMENT BY WINDOW","SELECT test_window_number,COUNT(*) AS days,AVG(CASE WHEN label_match THEN 1 ELSE 0 END)*100 AS agreement_pct,AVG(walk_forward_confidence)*100 mean_confidence_pct FROM latest_m25v_walk_forward_regimes GROUP BY test_window_number ORDER BY test_window_number")
    show(c,"HISTORICAL EVENT WINDOWS","SELECT event_name,event_date,observations,dominant_regime,dominant_share_pct,mean_macro_stress_pct,mean_volatility_shock_pct,mean_recovery_pct,coverage_status,regime_interpretation FROM latest_m25v_event_window_audit")
    show(c,"BEST ASSETS BY REGIME","SELECT regime,asset_id,observations,mean_next_30d_return_pct,median_next_30d_return_pct,positive_next_30d_rate_pct,annualized_daily_volatility_pct FROM latest_m25v_regime_asset_performance QUALIFY ROW_NUMBER() OVER(PARTITION BY regime ORDER BY mean_next_30d_return_pct DESC)<=3")
    show(c,"MODULE 13 HISTORY AUDIT","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m25v_module13_regime_audit")
    show(c,"PROBABILITY CALIBRATION","SELECT confidence_bin,observations,mean_predicted_persistence,observed_next_day_persistence,absolute_calibration_error FROM latest_m25v_probability_calibration")
    show(c,"PARAMETER SENSITIVITY","SELECT scenario_key,smoothing,rule_multiplier,risk_multiplier,recovery_multiplier,label_agreement_pct,mean_probability_shift,current_regime,current_confidence*100 current_confidence_pct FROM latest_m25v_parameter_sensitivity")
    show(c,"LATEST RUNS","SELECT started_at_utc,completed_at_utc,status,walk_forward_rows,event_rows,performance_rows,calibration_rows,sensitivity_rows,walk_forward_agreement_pct,calibration_error,sensitivity_stability_pct,validation_status,notes FROM module25v_runs ORDER BY started_at_utc DESC LIMIT 10")
    c.close()

if __name__=="__main__": main()
