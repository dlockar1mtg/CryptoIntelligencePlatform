from pathlib import Path
import shutil,yaml
ROOT=Path(__file__).resolve().parent
P=ROOT/"config"/"settings.yaml"
CONFIG={
"walk_forward":{"minimum_training_days":365,"test_days":90,"random_state":703},
"events":{"days_before":14,"days_after":30},
"validation":{
"minimum_walk_forward_agreement_pct":55,
"maximum_calibration_mae":0.20,
"minimum_sensitivity_stability_pct":70,
},
}
def main():
    if not P.exists(): raise FileNotFoundError(f"Missing settings: {P}")
    b=P.with_name("settings_before_v7_0_3.yaml")
    if not b.exists(): shutil.copy2(P,b); print(f"Settings backup: {b}")
    s=yaml.safe_load(P.read_text(encoding="utf-8")); s["module25_validation"]=CONFIG
    if "platform" in s: s["platform"]["version"]="7.0.3"
    P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding="utf-8")
    print("v7.0.3 configuration applied.")
if __name__=="__main__": main()
