from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module25 import MODULE25_SCHEMA

EXPORTS = {
    "latest_market_regime_features":
        "SELECT * FROM latest_market_regime_features",
    "market_regime_features":
        "SELECT * FROM m25_regime_features",
    "latest_market_regime_probabilities":
        "SELECT * FROM latest_market_regime_probabilities",
    "market_regime_probabilities":
        "SELECT * FROM m25_regime_probabilities",
    "latest_market_regime_daily":
        "SELECT * FROM latest_market_regime_daily",
    "market_regime_daily":
        "SELECT * FROM m25_regime_daily",
    "latest_market_regime_transitions":
        "SELECT * FROM latest_market_regime_transitions",
    "market_regime_transitions":
        "SELECT * FROM m25_regime_transitions",
    "latest_market_regime_durations":
        "SELECT * FROM latest_market_regime_durations",
    "market_regime_durations":
        "SELECT * FROM m25_regime_durations",
    "latest_market_regime_validation":
        "SELECT * FROM latest_market_regime_validation",
    "market_regime_validation":
        "SELECT * FROM m25_regime_validation",
    "latest_market_regime_contributions":
        "SELECT * FROM latest_market_regime_contributions",
    "market_regime_contributions":
        "SELECT * FROM m25_regime_contributions",
    "module25_runs":
        "SELECT * FROM module25_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE25_SCHEMA)
    directory = path_for(
        settings, "export_directory"
    )
    directory.mkdir(
        parents=True, exist_ok=True
    )

    for name, sql in EXPORTS.items():
        frame = conn.execute(sql).fetchdf()
        output = directory / f"{name}.csv"
        frame.to_csv(output, index=False)
        print(
            f"{name}: {len(frame)} rows -> {output}"
        )

    conn.close()

if __name__ == "__main__":
    main()
