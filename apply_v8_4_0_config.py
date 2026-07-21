from pathlib import Path
import shutil,yaml

ROOT=Path(__file__).resolve().parent
P=ROOT/"config"/"settings.yaml"

CONFIG={
"transaction_cost_bps":10,
"cost_sensitivity_bps":[10,25,50],
"drift":{"reference_days":120,"window_days":[30,60,90]},
"optimization":{
"rebalance_frequency_days":[1,7,14],
"rebalance_band_pct":[2.5,5.0,10.0],
"minimum_trade_pct":[1.0,2.5,5.0],
"exposure_smoothing_alpha":[0.10,0.20,0.35],
"annual_turnover_budget_pct":[100,150,250],
},
"validation":{
"maximum_turnover_pct":250,
"minimum_cost_pass_rate_pct":66.67,
},
}

def main():
    if not P.exists(): raise FileNotFoundError(f"Missing settings: {P}")
    b=P.with_name("settings_before_v8_4_0.yaml")
    if not b.exists():
        shutil.copy2(P,b); print(f"Settings backup: {b}")
    s=yaml.safe_load(P.read_text(encoding="utf-8"))
    s["module34"]=CONFIG
    if "platform" in s: s["platform"]["version"]="8.4.0"
    P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding="utf-8")
    print("v8.4.0 configuration applied.")

if __name__=="__main__":
    main()
