from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module39 import MODULE39_SCHEMA

EXPORTS={
"latest_m39_validation_summary":"SELECT * FROM latest_m39_validation_summary",
"latest_m39_probability_calibration":"SELECT * FROM latest_m39_probability_calibration",
"latest_m39_calibrated_forecasts":"SELECT * FROM latest_m39_calibrated_forecasts",
"latest_m39_rolling_origin_validation":"SELECT * FROM latest_m39_rolling_origin_validation",
"latest_m39_feature_stability":"SELECT * FROM latest_m39_feature_stability",
"latest_m39_forecast_drift":"SELECT * FROM latest_m39_forecast_drift",
"latest_m39_forecast_scorecard":"SELECT * FROM latest_m39_forecast_scorecard",
"module39_runs":"SELECT * FROM module39_runs",
}

def main():
    s,_=load_all();c=connect(s);c.execute(MODULE39_SCHEMA)
    d=path_for(s,"export_directory");d.mkdir(parents=True,exist_ok=True)
    for n,q in EXPORTS.items():
        f=c.execute(q).fetchdf();p=d/f"{n}.csv";f.to_csv(p,index=False)
        print(f"{n}: {len(f)} rows -> {p}")
    c.close()

if __name__=="__main__":main()
