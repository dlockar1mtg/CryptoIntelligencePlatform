from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module43 import MODULE43_SCHEMA


EXPORTS = {
    "latest_m43_committee_brief":
        "SELECT * FROM latest_m43_committee_brief",
    "latest_m43_opportunity_ranking":
        "SELECT * FROM latest_m43_opportunity_ranking",
    "latest_m43_decision_changes":
        "SELECT * FROM latest_m43_decision_changes",
    "latest_m43_action_triggers":
        "SELECT * FROM latest_m43_action_triggers",
    "latest_m43_thesis_monitor":
        "SELECT * FROM latest_m43_thesis_monitor",
    "latest_m43_buy_wait_analysis":
        "SELECT * FROM latest_m43_buy_wait_analysis",
    "module43_runs":
        "SELECT * FROM module43_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE43_SCHEMA)
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
