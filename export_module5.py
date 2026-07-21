from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA

EXPORTS = {
    "latest_multi_horizon_returns": "SELECT * FROM latest_multi_horizon_returns",
    "multi_horizon_returns": "SELECT * FROM multi_horizon_returns",
    "latest_cycle_analytics": "SELECT * FROM latest_cycle_analytics",
    "cycle_analytics": "SELECT * FROM cycle_analytics",
    "latest_expected_returns": "SELECT * FROM latest_expected_returns",
    "expected_returns": "SELECT * FROM expected_returns",
    "latest_optimized_allocations": "SELECT * FROM latest_optimized_allocations",
    "optimized_allocations": "SELECT * FROM optimized_allocations",
    "module5_runs": "SELECT * FROM module5_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    conn.execute(MODULE3_SCHEMA)
    conn.execute(MODULE5_SCHEMA)
    directory = path_for(settings, "export_directory")
    directory.mkdir(parents=True, exist_ok=True)
    for name, sql in EXPORTS.items():
        frame = conn.execute(sql).fetchdf()
        path = directory / f"{name}.csv"
        frame.to_csv(path, index=False)
        print(f"{name}: {len(frame)} rows -> {path}")
    conn.close()

if __name__ == "__main__":
    main()
