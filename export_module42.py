from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module42 import MODULE42_SCHEMA


EXPORTS = {
    "latest_m42_decision_summary":
        "SELECT * FROM latest_m42_decision_summary",
    "latest_m42_asset_recommendations":
        "SELECT * FROM latest_m42_asset_recommendations",
    "latest_m42_price_projections":
        "SELECT * FROM latest_m42_price_projections",
    "latest_m42_portfolio_plan":
        "SELECT * FROM latest_m42_portfolio_plan",
    "module42_runs":
        "SELECT * FROM module42_runs",
}


def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE42_SCHEMA)
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

    # Produce one wide, human-readable projection matrix.
    projection = conn.execute(
        """
        SELECT asset_id,
               horizon_label,
               bear_price,
               median_price,
               bull_price
        FROM latest_m42_price_projections
        ORDER BY asset_id, horizon_days
        """
    ).fetchdf()

    if not projection.empty:
        wide = projection.pivot(
            index="asset_id",
            columns="horizon_label",
            values=[
                "bear_price",
                "median_price",
                "bull_price",
            ],
        )
        wide.columns = [
            f"{scenario}_{horizon}"
            for scenario, horizon
            in wide.columns
        ]
        wide = wide.reset_index()
        output = (
            directory
            / "latest_m42_projection_matrix.csv"
        )
        wide.to_csv(output, index=False)
        print(
            f"latest_m42_projection_matrix: "
            f"{len(wide)} rows -> {output}"
        )

    conn.close()


if __name__ == "__main__":
    main()
