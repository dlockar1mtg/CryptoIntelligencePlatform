from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA

EXPORTS = {
    "canonical_history_coverage":
        "SELECT * FROM canonical_history_coverage",
    "canonical_market_daily":
        "SELECT * FROM canonical_market_daily ORDER BY asset_id,observation_date",
    "latest_model_snapshots":
        "SELECT * FROM latest_model_snapshots",
    "model_snapshots_daily":
        "SELECT * FROM model_snapshots_daily ORDER BY asset_id,observation_date",
    "signal_forward_performance":
        "SELECT * FROM signal_forward_performance ORDER BY asset_id,signal_date,horizon_days",
    "signal_validation_summary":
        "SELECT * FROM signal_validation_summary ORDER BY horizon_days,historical_signal",
    "cycle_transition_history":
        "SELECT * FROM cycle_transition_history ORDER BY transition_date,asset_id",
    "module6_runs":
        "SELECT * FROM module6_runs ORDER BY started_at_utc",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    for schema in [MODULE2_SCHEMA, MODULE3_SCHEMA, MODULE5_SCHEMA, MODULE6_SCHEMA]:
        conn.execute(schema)
    directory = path_for(settings, "export_directory")
    directory.mkdir(parents=True, exist_ok=True)
    for name, sql in EXPORTS.items():
        frame = conn.execute(sql).fetchdf()
        output = directory / f"{name}.csv"
        frame.to_csv(output, index=False)
        print(f"{name}: {len(frame)} rows -> {output}")
    conn.close()

if __name__ == "__main__":
    main()
