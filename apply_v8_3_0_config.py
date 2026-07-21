from pathlib import Path
import shutil,yaml

ROOT=Path(__file__).resolve().parent
P=ROOT/"config"/"settings.yaml"
CONFIG={
"feature_stability":{"minimum_training_days":365,"test_days":90},
"probability_drift":{"baseline_days":180,"window_days":[30,60,90]},
"retraining":{"minimum_training_days":365,"gradient_weight":0.60},
"benchmarks":{"transaction_cost_bps":10},
"validation":{
"maximum_retraining_log_loss":1.75,
"minimum_synthetic_pass_rate_pct":80,
},
}

def main():
    if not P.exists(): raise FileNotFoundError(f"Missing settings: {P}")
    b=P.with_name("settings_before_v8_3_0.yaml")
    if not b.exists(): shutil.copy2(P,b); print(f"Settings backup: {b}")
    s=yaml.safe_load(P.read_text(encoding="utf-8"))
    s["module32"]=CONFIG
    if "platform" in s: s["platform"]["version"]="8.3.0"
    P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding="utf-8")
    print("v8.3.0 configuration applied.")

if __name__=="__main__":
    main()
