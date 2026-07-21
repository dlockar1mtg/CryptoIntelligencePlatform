from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module35 import MODULE35_SCHEMA


EXPORTS = {
    "latest_m35_portfolio_allocations":
        "SELECT * FROM latest_m35_portfolio_allocations",
    "latest_m35_portfolio_candidates":
        "SELECT * FROM latest_m35_portfolio_candidates",
    "latest_m35_portfolio_correlations":
        "SELECT * FROM latest_m35_portfolio_correlations",
    "latest_m35_portfolio_statistics":
        "SELECT * FROM latest_m35_portfolio_statistics",
    "module35_runs":
        "SELECT * FROM module35_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE35_SCHEMA)
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
