from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module37 import MODULE37_SCHEMA


EXPORTS = {
    "latest_m37_expected_returns":
        "SELECT * FROM latest_m37_expected_returns",
    "latest_m37_optimizer_candidates":
        "SELECT * FROM latest_m37_optimizer_candidates",
    "latest_m37_optimized_allocations":
        "SELECT * FROM latest_m37_optimized_allocations",
    "latest_m37_risk_decomposition":
        "SELECT * FROM latest_m37_risk_decomposition",
    "latest_m37_efficient_frontier":
        "SELECT * FROM latest_m37_efficient_frontier",
    "latest_m37_portfolio_statistics":
        "SELECT * FROM latest_m37_portfolio_statistics",
    "module37_runs":
        "SELECT * FROM module37_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE37_SCHEMA)
    directory = path_for(
        settings,
        "export_directory",
    )
    directory.mkdir(
        parents=True,
        exist_ok=True,
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
