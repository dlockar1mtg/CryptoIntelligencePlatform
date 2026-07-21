from pathlib import Path
import pandas as pd
from crypto_platform.platform import load_all, connect, upsert

def main():
    settings, _ = load_all()
    directory = Path(settings["platform"]["database_path"]).parent
    if not directory.is_absolute():
        from crypto_platform.platform import ROOT
        directory = ROOT / "data" / "manual_macro"
    else:
        directory = directory.parent / "manual_macro"

    conn = connect(settings)
    catalog = {
        row["series_id"]: row["series_key"]
        for row in settings["macro_series"]
    }
    imported = 0
    for path in sorted(directory.glob("*.csv")):
        series_id = path.stem.upper()
        if series_id not in catalog:
            print(f"Skipped unconfigured series: {path.name}")
            continue
        frame = pd.read_csv(path)
        required = {"observation_date", "value"}
        if not required.issubset(frame.columns):
            print(f"Skipped {path.name}: required columns are {sorted(required)}")
            continue
        frame = frame[["observation_date", "value"]].copy()
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"], errors="coerce"
        ).dt.date
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame = frame.dropna()
        frame["series_key"] = catalog[series_id]
        frame["source"] = "manual_crypto_import"
        frame["collected_at_utc"] = pd.Timestamp.now(tz="UTC")
        frame = frame[[
            "series_key", "observation_date", "value",
            "source", "collected_at_utc",
        ]]
        inserted, updated = upsert(
            conn, "macro_observations", frame,
            ["series_key", "observation_date", "source"],
        )
        imported += len(frame)
        print(
            f"{path.name}: {len(frame)} rows "
            f"({inserted} inserted, {updated} updated)"
        )
    conn.close()
    print(f"Manual macro import complete: {imported} rows processed.")

if __name__ == "__main__":
    main()
