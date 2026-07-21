from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module44 import MODULE44_SCHEMA

EXPORTS = {
    "latest_m44_economic_value_summary": "SELECT * FROM latest_m44_economic_value_summary",
    "latest_m44_decision_outcomes": "SELECT * FROM latest_m44_decision_outcomes",
    "latest_m44_benchmark_comparison": "SELECT * FROM latest_m44_benchmark_comparison",
    "latest_m44_action_value": "SELECT * FROM latest_m44_action_value",
    "latest_m44_timing_value": "SELECT * FROM latest_m44_timing_value",
    "latest_m44_horizon_value": "SELECT * FROM latest_m44_horizon_value",
    "latest_m44_portfolio_value": "SELECT * FROM latest_m44_portfolio_value",
    "module44_runs": "SELECT * FROM module44_runs",
}


def main():
    s, _ = load_all()
    c = connect(s)
    c.execute(MODULE44_SCHEMA)
    d = path_for(s, "export_directory")
    d.mkdir(parents=True, exist_ok=True)
    for name, sql in EXPORTS.items():
        f = c.execute(sql).fetchdf()
        p = d / f"{name}.csv"
        f.to_csv(p, index=False)
        print(f"{name}: {len(f)} rows -> {p}")
    c.close()


if __name__ == "__main__":
    main()
