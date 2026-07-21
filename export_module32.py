from crypto_platform.platform import load_all,connect,path_for
from crypto_platform.module32 import MODULE32_SCHEMA

EXPORTS={
"latest_m32_validation_summary":"SELECT * FROM latest_m32_validation_summary",
"latest_m32_feature_stability_history":"SELECT * FROM latest_m32_feature_stability_history",
"latest_m32_feature_stability_summary":"SELECT * FROM latest_m32_feature_stability_summary",
"latest_m32_probability_drift":"SELECT * FROM latest_m32_probability_drift",
"latest_m32_retraining_policy_validation":"SELECT * FROM latest_m32_retraining_policy_validation",
"latest_m32_historical_stress_validation":"SELECT * FROM latest_m32_historical_stress_validation",
"latest_m32_synthetic_stress_validation":"SELECT * FROM latest_m32_synthetic_stress_validation",
"latest_m32_benchmark_daily":"SELECT * FROM latest_m32_benchmark_daily",
"latest_m32_benchmark_summary":"SELECT * FROM latest_m32_benchmark_summary",
"module32_runs":"SELECT * FROM module32_runs",
}

def main():
    s,_=load_all(); c=connect(s); c.execute(MODULE32_SCHEMA)
    d=path_for(s,"export_directory"); d.mkdir(parents=True,exist_ok=True)
    for n,q in EXPORTS.items():
        f=c.execute(q).fetchdf(); p=d/f"{n}.csv"; f.to_csv(p,index=False)
        print(f"{n}: {len(f)} rows -> {p}")
    c.close()

if __name__=="__main__":
    main()
