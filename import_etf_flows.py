from pathlib import Path
import pandas as pd
from crypto_platform.platform import load_all

def main():
    settings, _ = load_all()
    path = Path(settings["module17"]["manual_inputs"]["etf_flows_csv"])
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f"ETF flow file already exists: {path}")
        return
    pd.DataFrame(columns=[
        "observation_date", "net_flow_usd", "source"
    ]).to_csv(path, index=False)
    print(f"Created template: {path}")
    print("Add validated daily net-flow observations, then rerun Module 17.")

if __name__ == "__main__":
    main()
