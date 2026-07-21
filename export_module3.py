from crypto_platform.platform import load_all, connect, path_for
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA

EXPORTS = {
    "latest_portfolio_recommendations":
        "SELECT * FROM latest_portfolio_recommendations",
    "portfolio_recommendations":
        "SELECT * FROM portfolio_recommendations",
    "latest_portfolio_summary":
        "SELECT * FROM latest_portfolio_summary",
    "portfolio_summary":
        "SELECT * FROM portfolio_summary",
    "latest_risk_metrics":
        "SELECT * FROM latest_risk_metrics",
    "asset_risk_metrics":
        "SELECT * FROM asset_risk_metrics",
    "latest_scenario_projections":
        "SELECT * FROM latest_scenario_projections",
    "scenario_projections":
        "SELECT * FROM scenario_projections",
    "asset_correlations":
        "SELECT * FROM asset_correlations",
    "latest_valuation_zones":
        "SELECT * FROM latest_valuation_zones",
    "valuation_zones":
        "SELECT * FROM valuation_zones",
    "latest_rebalance_recommendations":
        "SELECT * FROM latest_rebalance_recommendations",
    "rebalance_recommendations":
        "SELECT * FROM rebalance_recommendations",
    "latest_position_risk_contributions":
        "SELECT * FROM latest_position_risk_contributions",
    "position_risk_contributions":
        "SELECT * FROM position_risk_contributions",
    "module3_runs":
        "SELECT * FROM module3_runs",
}

def main():
    settings, _ = load_all()
    conn = connect(settings)
    conn.execute(MODULE2_SCHEMA)
    conn.execute(MODULE3_SCHEMA)
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
