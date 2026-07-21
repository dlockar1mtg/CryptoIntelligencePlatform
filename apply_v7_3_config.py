from pathlib import Path
import shutil,yaml

ROOT=Path(__file__).resolve().parent
SETTINGS=ROOT/"config"/"settings.yaml"

CONFIG={
"models":{"random_state":730},
"feature_selection":{
"permutation_repeats":8,
"minimum_core_features":6,
"maximum_features":12,
"maximum_pairwise_correlation":0.88,
},
"adaptive_search":{
"seed":730,
"initial_candidates":140,
"generation_candidates":100,
"generations":3,
"elite_count":18,
},
"meta_ensemble":{
"top_candidates":5,
"temperature":4.0,
},
"nested_walk_forward":{
"minimum_training_days":540,
"inner_validation_days":120,
"outer_test_days":90,
},
"robustness":{
"initial_candidates":60,
"generation_candidates":40,
"generations":2,
},
"validation":{
"minimum_nested_agreement_pct":55,
"maximum_calibrated_mae":0.15,
"minimum_meta_stability_pct":75,
},
}

def main():
    if not SETTINGS.exists():
        raise FileNotFoundError(f"Missing settings: {SETTINGS}")
    backup=SETTINGS.with_name("settings_before_v7_3.yaml")
    if not backup.exists():
        shutil.copy2(SETTINGS,backup)
        print(f"Settings backup: {backup}")
    settings=yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))
    settings["module28"]=CONFIG
    if "platform" in settings:
        settings["platform"]["version"]="7.3.0"
    SETTINGS.write_text(
        yaml.safe_dump(settings,sort_keys=False,allow_unicode=True),
        encoding="utf-8",
    )
    print("v7.3 configuration applied.")

if __name__=="__main__":
    main()
