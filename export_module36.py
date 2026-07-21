from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module36 import MODULE36_SCHEMA


EXPORTS = {
    "latest_m36_asset_risk":
        "SELECT * FROM latest_m36_asset_risk",
    "latest_m36_portfolio_risk":
        "SELECT * FROM latest_m36_portfolio_risk",
    "latest_m36_risk_adjusted_allocations":
        "SELECT * FROM latest_m36_risk_adjusted_allocations",
    "module36_runs":
        "SELECT * FROM module36_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE36_SCHEMA)
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
