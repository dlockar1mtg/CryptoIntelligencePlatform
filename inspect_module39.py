from crypto_platform.platform import load_all,connect
from crypto_platform.module39 import MODULE39_SCHEMA

def show(c,t,q):
    print(f"\n{t}\n{'-'*len(t)}")
    f=c.execute(q).fetchdf()
    print(f.to_string(index=False) if not f.empty else "No data.")

def main():
    s,_=load_all();c=connect(s);c.execute(MODULE39_SCHEMA)
    show(c,"VALIDATION SUMMARY","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m39_validation_summary")
    show(c,"CALIBRATED FORECASTS","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m39_calibrated_forecasts")
    show(c,"PROBABILITY CALIBRATION","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m39_probability_calibration")
    show(c,"ROLLING-ORIGIN VALIDATION","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m39_rolling_origin_validation")
    show(c,"FEATURE STABILITY","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m39_feature_stability")
    show(c,"FORECAST DRIFT","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m39_forecast_drift")
    show(c,"REALIZED FORECAST SCORECARD","SELECT * EXCLUDE(run_id,calculated_at_utc) FROM latest_m39_forecast_scorecard")
    show(c,"LATEST RUNS","SELECT * FROM module39_runs ORDER BY started_at_utc DESC LIMIT 10")
    c.close()

if __name__=="__main__":main()
