from pathlib import Path
import shutil,yaml

ROOT=Path(__file__).resolve().parent
P=ROOT/"config"/"settings.yaml"
CONFIG={"minimum_matured_forecasts":30}

def main():
    if not P.exists():raise FileNotFoundError(P)
    b=P.with_name("settings_before_v11_0_0.yaml")
    if not b.exists():shutil.copy2(P,b);print(f"Settings backup: {b}")
    s=yaml.safe_load(P.read_text(encoding="utf-8"))
    s["module41"]=CONFIG
    if "platform" in s:s["platform"]["version"]="11.0.0"
    P.write_text(yaml.safe_dump(s,sort_keys=False,allow_unicode=True),encoding="utf-8")
    print("v11.0.0 configuration applied.")
    print("v10.2.1 canonical forecast identity enabled.")

if __name__=="__main__":main()
