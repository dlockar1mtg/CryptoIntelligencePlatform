from pathlib import Path
import shutil,yaml

ROOT=Path(__file__).resolve().parent
P=ROOT/"config"/"settings.yaml"
CONFIG={
"conformal_alpha":0.10,
"rolling_folds":3,
"minimum_training_rows":90,
"validation":{
"maximum_brier":0.25,
"minimum_interval_coverage_pct":80.0,
"minimum_directional_accuracy_pct":55.0,
},
}

def main():
    if not P.exists():raise FileNotFoundError(P)
    b=P.with_name("settings_before_v10_1_0.yaml")
    if not b.exists():shutil.copy2(P,b);print(f"Settings backup: {b}")
    s=yaml.safe_load(P.read_text(encoding="utf-8"))
    s["module39"]=CONFIG
    if "platform" in s:s["platform"]["version"]="10.1.0"
    P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding="utf-8")
    print("v10.1.0 configuration applied.")

if __name__=="__main__":main()
